from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
STRESS TEST: Rapid Page Refresh Scenarios

This test suite stress-tests the system under rapid, concurrent page refreshes
to ensure stability, prevent resource leaks, and maintain performance.

CRITICAL: System must handle aggressive refresh patterns without degradation.

@compliance CLAUDE.md - System stability and user experience
@performance Target: Handle 100+ refreshes without memory leaks or crashes
"""

import asyncio
import json
import time
import psutil
import gc
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import jwt
import pytest
from playwright.async_api import Page, Browser, BrowserContext, async_playwright
import os
import sys
import tracemalloc

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from test_framework.test_context import TestContext


class RapidRefreshStressTests:
    """Stress tests for rapid page refresh scenarios."""
    
    def __init__(self):
        self.frontend_url = get_env().get('FRONTEND_URL', 'http://localhost:3000')
        self.backend_url = get_env().get('BACKEND_URL', 'http://localhost:8000')
        self.jwt_secret = get_env().get('JWT_SECRET', 'test-secret-key')
        self.test_results: Dict[str, Any] = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'performance_degradation': [],
            'memory_leaks': [],
            'resource_metrics': {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        # Start memory tracking
        tracemalloc.start()
        self.process = psutil.Process()
    
    def generate_test_token(self, user_id: str = "stress_user") -> str:
        """Generate a valid JWT token for testing."""
        payload = {
            'sub': user_id,
            'email': f'{user_id}@stress.test',
            'exp': int(time.time()) + 3600,
            'iat': int(time.time())
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage metrics."""
        memory_info = self.process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
            'percent': self.process.memory_percent()
        }
    
    def get_resource_metrics(self) -> Dict[str, Any]:
        """Get comprehensive resource metrics."""
        return {
            'memory': self.get_memory_usage(),
            'cpu_percent': self.process.cpu_percent(interval=0.1),
            'num_threads': self.process.num_threads(),
            'num_fds': len(self.process.open_files()) if hasattr(self.process, 'open_files') else 0,
            'connections': len(self.process.connections())
        }
    
    async def test_sequential_rapid_refresh(self, browser: Browser) -> bool:
        """
        Test rapid sequential page refreshes.
        Simulates user frantically hitting F5.
        """
        test_name = "sequential_rapid_refresh"
        print(f"\n SEARCH:  Testing: {test_name}")
        
        try:
            context = await browser.new_context()
            page = await context.new_page()
            
            # Setup authentication
            token = self.generate_test_token("sequential_user")
            await page.evaluate(f"""
                localStorage.setItem('jwt_token', '{token}');
            """)
            
            # Initial load
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            
            # Metrics tracking
            refresh_times = []
            errors_encountered = []
            initial_memory = self.get_memory_usage()
            
            # Perform rapid refreshes
            refresh_count = 20
            for i in range(refresh_count):
                start_time = time.time()
                
                try:
                    # Don't wait for full load, simulate impatient user
                    await page.reload(wait_until='domcontentloaded', timeout=5000)
                    
                    # Small random delay to simulate human behavior
                    await page.wait_for_timeout(100 + (i % 3) * 50)
                    
                    refresh_times.append(time.time() - start_time)
                    
                    # Check for errors every 5 refreshes
                    if i % 5 == 0:
                        console_errors = await page.evaluate("""
                            window.consoleErrors || []
                        """)
                        if console_errors:
                            errors_encountered.extend(console_errors)
                    
                except Exception as e:
                    errors_encountered.append(str(e))
                    if len(errors_encountered) > 5:
                        break
            
            # Final checks
            final_memory = self.get_memory_usage()
            memory_increase = final_memory['rss_mb'] - initial_memory['rss_mb']
            
            # Check for memory leak
            if memory_increase > 50:  # More than 50MB increase
                self.test_results['memory_leaks'].append({
                    'test': test_name,
                    'increase_mb': memory_increase
                })
                print(f" WARNING: [U+FE0F] Memory increase detected: {memory_increase:.2f}MB")
            
            # Check for performance degradation
            if len(refresh_times) > 10:
                first_half_avg = sum(refresh_times[:10]) / 10
                second_half_avg = sum(refresh_times[10:]) / len(refresh_times[10:])
                
                if second_half_avg > first_half_avg * 1.5:
                    self.test_results['performance_degradation'].append({
                        'test': test_name,
                        'degradation': (second_half_avg / first_half_avg - 1) * 100
                    })
                    print(f" WARNING: [U+FE0F] Performance degradation: {(second_half_avg / first_half_avg - 1) * 100:.1f}%")
            
            # Verify chat still works
            await page.wait_for_selector('[data-testid="main-chat"], .chat-interface', timeout=5000)
            
            await context.close()
            
            if len(errors_encountered) > refresh_count * 0.1:  # More than 10% errors
                raise AssertionError(f"Too many errors: {len(errors_encountered)}/{refresh_count}")
            
            print(f" PASS:  {test_name}: Handled {refresh_count} rapid refreshes")
            print(f"   Average refresh time: {sum(refresh_times)/len(refresh_times):.2f}s")
            self.test_results['passed'] += 1
            return True
            
        except Exception as e:
            print(f" FAIL:  {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
    
    async def test_concurrent_refresh_multiple_tabs(self, browser: Browser) -> bool:
        """
        Test multiple tabs refreshing concurrently.
        Simulates multiple browser tabs being refreshed simultaneously.
        """
        test_name = "concurrent_refresh_multiple_tabs"
        print(f"\n SEARCH:  Testing: {test_name}")
        
        try:
            num_tabs = 5
            contexts = []
            pages = []
            
            # Create multiple tabs
            for i in range(num_tabs):
                context = await browser.new_context()
                page = await context.new_page()
                
                # Setup authentication
                token = self.generate_test_token(f"concurrent_user_{i}")
                await page.evaluate(f"""
                    localStorage.setItem('jwt_token', '{token}');
                """)
                
                await page.goto(f"{self.frontend_url}/chat", wait_until='domcontentloaded')
                
                contexts.append(context)
                pages.append(page)
            
            initial_metrics = self.get_resource_metrics()
            
            # Concurrent refresh function
            async def refresh_page(page: Page, page_id: int) -> Dict[str, Any]:
                refresh_times = []
                errors = []
                
                for j in range(10):  # 10 refreshes per tab
                    try:
                        start = time.time()
                        await page.reload(wait_until='domcontentloaded', timeout=5000)
                        refresh_times.append(time.time() - start)
                        await asyncio.sleep(0.2)  # Small delay between refreshes
                    except Exception as e:
                        errors.append(str(e))
                
                return {
                    'page_id': page_id,
                    'refresh_times': refresh_times,
                    'errors': errors
                }
            
            # Run concurrent refreshes
            tasks = [refresh_page(page, i) for i, page in enumerate(pages)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            total_refreshes = 0
            total_errors = 0
            all_refresh_times = []
            
            for result in results:
                if isinstance(result, Exception):
                    total_errors += 1
                else:
                    total_refreshes += len(result['refresh_times'])
                    total_errors += len(result['errors'])
                    all_refresh_times.extend(result['refresh_times'])
            
            final_metrics = self.get_resource_metrics()
            
            # Check resource usage
            memory_increase = final_metrics['memory']['rss_mb'] - initial_metrics['memory']['rss_mb']
            cpu_usage = final_metrics['cpu_percent']
            
            # Clean up
            for context in contexts:
                await context.close()
            
            # Verify no excessive resource usage
            if memory_increase > 100:  # More than 100MB for multiple tabs
                self.test_results['memory_leaks'].append({
                    'test': test_name,
                    'increase_mb': memory_increase,
                    'tabs': num_tabs
                })
                print(f" WARNING: [U+FE0F] High memory usage: {memory_increase:.2f}MB for {num_tabs} tabs")
            
            if cpu_usage > 80:
                print(f" WARNING: [U+FE0F] High CPU usage: {cpu_usage:.1f}%")
            
            error_rate = total_errors / (total_refreshes + total_errors) if total_refreshes > 0 else 1
            if error_rate > 0.2:  # More than 20% error rate
                raise AssertionError(f"High error rate: {error_rate:.1%}")
            
            print(f" PASS:  {test_name}: {num_tabs} tabs handled {total_refreshes} refreshes")
            print(f"   Average refresh time: {sum(all_refresh_times)/len(all_refresh_times):.2f}s")
            print(f"   Memory increase: {memory_increase:.2f}MB")
            self.test_results['passed'] += 1
            return True
            
        except Exception as e:
            print(f" FAIL:  {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
    
    async def test_refresh_during_active_operations(self, browser: Browser) -> bool:
        """
        Test refreshing while operations are in progress.
        Simulates refresh during message sending, agent processing, etc.
        """
        test_name = "refresh_during_active_operations"
        print(f"\n SEARCH:  Testing: {test_name}")
        
        try:
            context = await browser.new_context()
            page = await context.new_page()
            
            # Setup authentication
            token = self.generate_test_token("active_ops_user")
            await page.evaluate(f"""
                localStorage.setItem('jwt_token', '{token}');
            """)
            
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            
            errors_caught = []
            successful_operations = 0
            
            for i in range(10):
                try:
                    # Start an operation (send message)
                    message_input = await page.query_selector('[data-testid="message-input"], textarea')
                    if message_input:
                        await message_input.fill(f"Test message {i}")
                        # Don't wait for send to complete
                        await message_input.press("Enter", delay=0)
                    
                    # Immediately refresh (simulating impatient user)
                    await asyncio.sleep(0.1)  # Very brief delay
                    await page.reload(wait_until='domcontentloaded', timeout=5000)
                    
                    # Check if chat is still functional
                    await page.wait_for_selector('[data-testid="main-chat"], .chat-interface', timeout=3000)
                    successful_operations += 1
                    
                except Exception as e:
                    errors_caught.append(str(e))
            
            await context.close()
            
            # Allow some errors during active operations
            error_rate = len(errors_caught) / 10
            if error_rate > 0.5:  # More than 50% failure
                raise AssertionError(f"High failure rate during active operations: {error_rate:.1%}")
            
            print(f" PASS:  {test_name}: {successful_operations}/10 operations survived refresh")
            self.test_results['passed'] += 1
            return True
            
        except Exception as e:
            print(f" FAIL:  {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
    
    async def test_memory_leak_detection(self, browser: Browser) -> bool:
        """
        Dedicated test for memory leak detection during refreshes.
        Performs many refreshes and monitors memory growth.
        """
        test_name = "memory_leak_detection"
        print(f"\n SEARCH:  Testing: {test_name}")
        
        try:
            context = await browser.new_context()
            page = await context.new_page()
            
            # Setup authentication
            token = self.generate_test_token("memory_test_user")
            await page.evaluate(f"""
                localStorage.setItem('jwt_token', '{token}');
            """)
            
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            
            # Force garbage collection
            gc.collect()
            initial_memory = self.get_memory_usage()
            memory_samples = [initial_memory['rss_mb']]
            
            # Perform many refreshes with memory sampling
            refresh_count = 50
            sample_interval = 10
            
            for i in range(refresh_count):
                await page.reload(wait_until='domcontentloaded', timeout=5000)
                
                if (i + 1) % sample_interval == 0:
                    # Force garbage collection before sampling
                    gc.collect()
                    await asyncio.sleep(1)  # Allow cleanup
                    
                    current_memory = self.get_memory_usage()
                    memory_samples.append(current_memory['rss_mb'])
                    
                    print(f"   Memory after {i+1} refreshes: {current_memory['rss_mb']:.2f}MB")
            
            await context.close()
            
            # Analyze memory growth
            memory_growth_rate = (memory_samples[-1] - memory_samples[0]) / refresh_count
            total_growth = memory_samples[-1] - memory_samples[0]
            
            # Check for linear growth (indicates leak)
            is_linear_growth = all(
                memory_samples[i] <= memory_samples[i+1] + 5  # Allow 5MB variance
                for i in range(len(memory_samples)-1)
            )
            
            self.test_results['resource_metrics']['memory_growth'] = {
                'initial_mb': memory_samples[0],
                'final_mb': memory_samples[-1],
                'total_growth_mb': total_growth,
                'growth_per_refresh_mb': memory_growth_rate,
                'samples': memory_samples
            }
            
            # Thresholds
            if memory_growth_rate > 1.0:  # More than 1MB per refresh
                raise AssertionError(f"Memory leak detected: {memory_growth_rate:.2f}MB per refresh")
            
            if total_growth > 50:  # More than 50MB total
                print(f" WARNING: [U+FE0F] High memory growth: {total_growth:.2f}MB")
                self.test_results['memory_leaks'].append({
                    'test': test_name,
                    'total_growth_mb': total_growth,
                    'per_refresh_mb': memory_growth_rate
                })
            
            print(f" PASS:  {test_name}: Memory growth acceptable ({memory_growth_rate:.3f}MB/refresh)")
            self.test_results['passed'] += 1
            return True
            
        except Exception as e:
            print(f" FAIL:  {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
    
    async def test_websocket_connection_limits(self, browser: Browser) -> bool:
        """
        Test WebSocket connection limits during rapid refreshes.
        Ensures old connections are properly closed and not leaked.
        """
        test_name = "websocket_connection_limits"
        print(f"\n SEARCH:  Testing: {test_name}")
        
        try:
            context = await browser.new_context()
            page = await context.new_page()
            
            # Monitor WebSocket connections
            ws_connections = []
            
            def handle_websocket(ws):
                ws_connections.append({
                    'url': ws.url,
                    'opened_at': time.time(),
                    'closed': False
                })
                ws.on('close', lambda: ws_connections[-1].update({'closed': True, 'closed_at': time.time()}))
            
            page.on('websocket', handle_websocket)
            
            # Setup authentication
            token = self.generate_test_token("ws_limit_user")
            await page.evaluate(f"""
                localStorage.setItem('jwt_token', '{token}');
            """)
            
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            
            # Rapid refreshes
            for i in range(20):
                await page.reload(wait_until='domcontentloaded', timeout=5000)
                await asyncio.sleep(0.2)
            
            # Wait a bit for connections to close
            await asyncio.sleep(2)
            
            # Analyze connections
            total_connections = len(ws_connections)
            open_connections = sum(1 for conn in ws_connections if not conn['closed'])
            
            # Check for connection leaks
            if open_connections > 2:  # Should only have 1 active, allow 2 for transition
                print(f" WARNING: [U+FE0F] {open_connections} WebSocket connections still open")
            
            if total_connections > 25:  # Should be close to refresh count
                print(f" WARNING: [U+FE0F] Excessive WebSocket connections created: {total_connections}")
            
            await context.close()
            
            # Verify proper cleanup
            if open_connections > 3:
                raise AssertionError(f"WebSocket connection leak: {open_connections} connections still open")
            
            print(f" PASS:  {test_name}: WebSocket connections properly managed")
            print(f"   Total created: {total_connections}, Still open: {open_connections}")
            self.test_results['passed'] += 1
            return True
            
        except Exception as e:
            print(f" FAIL:  {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
    
    async def run_all_tests(self, browser: Browser) -> Dict[str, Any]:
        """Run all rapid refresh stress tests."""
        print("\n" + "=" * 60)
        print("[U+1F4A8] STRESS TEST: Rapid Page Refresh Suite")
        print("=" * 60)
        
        initial_resources = self.get_resource_metrics()
        
        tests = [
            self.test_sequential_rapid_refresh,
            self.test_concurrent_refresh_multiple_tabs,
            self.test_refresh_during_active_operations,
            self.test_memory_leak_detection,
            self.test_websocket_connection_limits
        ]
        
        for test_func in tests:
            try:
                # Run garbage collection between tests
                gc.collect()
                await asyncio.sleep(1)
                
                await test_func(browser)
            except Exception as e:
                print(f" FAIL:  Unexpected error in {test_func.__name__}: {str(e)}")
                self.test_results['failed'] += 1
                self.test_results['total'] += 1
        
        final_resources = self.get_resource_metrics()
        
        # Store overall resource usage
        self.test_results['resource_metrics']['overall'] = {
            'initial': initial_resources,
            'final': final_resources,
            'memory_increase_mb': final_resources['memory']['rss_mb'] - initial_resources['memory']['rss_mb'],
            'peak_cpu': final_resources['cpu_percent']
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print(" CHART:  STRESS TEST RESULTS SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.test_results['total']}")
        print(f"Passed: {self.test_results['passed']}  PASS: ")
        print(f"Failed: {self.test_results['failed']}  FAIL: ")
        
        if self.test_results['memory_leaks']:
            print("\n WARNING: [U+FE0F] MEMORY LEAK WARNINGS:")
            for leak in self.test_results['memory_leaks']:
                print(f"  - {leak['test']}: {leak.get('increase_mb', 'N/A')}MB increase")
        
        if self.test_results['performance_degradation']:
            print("\n WARNING: [U+FE0F] PERFORMANCE DEGRADATION:")
            for deg in self.test_results['performance_degradation']:
                print(f"  - {deg['test']}: {deg['degradation']:.1f}% slower")
        
        overall_metrics = self.test_results['resource_metrics'].get('overall', {})
        if overall_metrics:
            print("\n[U+1F4C8] OVERALL RESOURCE USAGE:")
            print(f"  Memory increase: {overall_metrics['memory_increase_mb']:.2f}MB")
            print(f"  Peak CPU: {overall_metrics['peak_cpu']:.1f}%")
        
        # Determine overall status
        critical_issues = len(self.test_results['memory_leaks']) + len(self.test_results['performance_degradation'])
        
        if self.test_results['failed'] == 0 and critical_issues == 0:
            print("\n PASS:  ALL STRESS TESTS PASSED - System handles rapid refresh excellently!")
        elif critical_issues > 0:
            print(f"\n WARNING: [U+FE0F] {critical_issues} PERFORMANCE ISSUES DETECTED - Review resource management")
        else:
            print(f"\n FAIL:  {self.test_results['failed']} TESTS FAILED - System stability issues detected")
        
        return self.test_results


# Pytest integration
@pytest.mark.asyncio
@pytest.mark.stress
async def test_rapid_refresh_stress():
    """Pytest wrapper for rapid refresh stress tests."""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-dev-shm-usage', '--no-sandbox']  # Optimize for CI
        )
        
        try:
            test_suite = RapidRefreshStressTests()
            results = await test_suite.run_all_tests(browser)
            
            # Assert no critical failures
            assert results['failed'] <= 1, f"Too many failures: {results['failed']}"
            
            # Assert no severe memory leaks
            severe_leaks = [l for l in results['memory_leaks'] if l.get('increase_mb', 0) > 100]
            assert len(severe_leaks) == 0, f"Severe memory leaks detected: {severe_leaks}"
            
        finally:
            await browser.close()


if __name__ == "__main__":
    # Allow running directly for debugging
    import asyncio
    from playwright.async_api import async_playwright
    
    async def main():
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Visible for debugging
                args=['--disable-dev-shm-usage']
            )
            
            try:
                test_suite = RapidRefreshStressTests()
                results = await test_suite.run_all_tests(browser)
                
                # Exit with appropriate code
                critical_issues = len(results['memory_leaks']) + results['failed']
                sys.exit(0 if critical_issues == 0 else 1)
                
            finally:
                await browser.close()
                tracemalloc.stop()
    
    asyncio.run(main())
