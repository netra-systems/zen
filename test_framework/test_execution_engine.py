#!/usr/bin/env python
"""
Test Execution Engine - Handles parallel and sequential test execution
Manages test running with timeout, retry logic, and result collection
"""

import sys
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from .test_profile_models import TestProfile, TestStatus


class TestExecutionEngine:
    """Handles test execution with parallel/sequential modes and retry logic"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
    async def execute_parallel(
        self,
        tests: List[TestProfile],
        max_parallel: int,
        fail_fast: bool = False
    ) -> List[Dict]:
        """Execute tests in parallel"""
        results = []
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def run_test(test: TestProfile):
            async with semaphore:
                if fail_fast and any(r["status"] == "failed" for r in results):
                    return {"name": test.name, "status": "skipped", "reason": "fail_fast"}
                
                result = await self._run_single_test(test)
                results.append(result)
                return result
        
        tasks = [run_test(test) for test in tests]
        await asyncio.gather(*tasks)
        
        return results
    
    async def execute_sequential(
        self,
        tests: List[TestProfile],
        fail_fast: bool = False
    ) -> List[Dict]:
        """Execute tests sequentially"""
        results = []
        
        for test in tests:
            if fail_fast and any(r["status"] == "failed" for r in results):
                results.append({"name": test.name, "status": "skipped", "reason": "fail_fast"})
                continue
            
            result = await self._run_single_test(test)
            results.append(result)
        
        return results
    
    async def _run_single_test(self, test: TestProfile) -> Dict:
        """Run a single test and return result"""
        start_time = time.time()
        
        # Prepare test command based on test type
        if test.path.endswith(".py"):
            cmd = [sys.executable, "-m", "pytest", test.path, "-xvs", "--tb=short"]
        elif test.path.endswith((".ts", ".tsx", ".js", ".jsx")):
            cmd = ["npm", "test", "--", test.path]
        else:
            return {
                "name": test.name,
                "path": test.path,
                "status": "error",
                "error": "Unknown test type",
                "duration": 0
            }
        
        try:
            # Run test with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=test.avg_duration * 2 if test.avg_duration > 0 else 60
                )
                
                duration = time.time() - start_time
                status = TestStatus.PASSED if process.returncode == 0 else TestStatus.FAILED
                
                # Update test profile
                test.update_result(status, duration)
                
                return {
                    "name": test.name,
                    "path": test.path,
                    "status": status.value,
                    "duration": duration,
                    "output": stdout.decode() if stdout else "",
                    "error": stderr.decode() if stderr and process.returncode != 0 else "",
                    "exit_code": process.returncode,
                    "timestamp": datetime.now().isoformat()
                }
                
            except asyncio.TimeoutError:
                process.kill()
                duration = time.time() - start_time
                test.update_result(TestStatus.TIMEOUT, duration)
                
                return {
                    "name": test.name,
                    "path": test.path,
                    "status": "timeout",
                    "duration": duration,
                    "error": f"Test timed out after {duration:.2f}s",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            duration = time.time() - start_time
            test.update_result(TestStatus.ERROR, duration)
            
            return {
                "name": test.name,
                "path": test.path,
                "status": "error",
                "duration": duration,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def retry_failed_tests(
        self, 
        failed_tests: List[Dict], 
        test_profiles: Dict[str, TestProfile],
        retry_count: int = 1
    ) -> List[Dict]:
        """Retry failed tests"""
        retry_results = []
        
        for test_result in failed_tests:
            test_name = test_result["name"]
            test_profile = test_profiles.get(test_name)
            
            if not test_profile:
                continue
            
            best_result = test_result
            for i in range(retry_count):
                print(f"Retrying {test_name} (attempt {i+1}/{retry_count})")
                retry_result = await self._run_single_test(test_profile)
                
                if retry_result["status"] == "passed":
                    best_result = retry_result
                    best_result["retried"] = True
                    best_result["retry_attempt"] = i + 1
                    break
            
            retry_results.append(best_result)
        
        return retry_results
    
    def generate_execution_summary(self, test_results: List[Dict]) -> Dict:
        """Generate test execution summary"""
        summary = {
            "total": len(test_results),
            "passed": sum(1 for t in test_results if t["status"] == "passed"),
            "failed": sum(1 for t in test_results if t["status"] == "failed"),
            "skipped": sum(1 for t in test_results if t["status"] == "skipped"),
            "errors": sum(1 for t in test_results if t["status"] == "error"),
            "timeouts": sum(1 for t in test_results if t["status"] == "timeout"),
            "retried": sum(1 for t in test_results if t.get("retried", False)),
            "total_duration": sum(t.get("duration", 0) for t in test_results),
            "avg_duration": sum(t.get("duration", 0) for t in test_results) / len(test_results) if test_results else 0
        }
        
        summary["pass_rate"] = (summary["passed"] / summary["total"] * 100) if summary["total"] > 0 else 0
        
        return summary


class BatchTestExecutor:
    """Executes tests in batches for memory management"""
    
    def __init__(self, execution_engine: TestExecutionEngine, batch_size: int = 50):
        self.execution_engine = execution_engine
        self.batch_size = batch_size
    
    async def execute_in_batches(
        self, 
        tests: List[TestProfile], 
        max_parallel: int = 4,
        fail_fast: bool = False
    ) -> List[Dict]:
        """Execute tests in batches to manage memory"""
        all_results = []
        
        for i in range(0, len(tests), self.batch_size):
            batch = tests[i:i + self.batch_size]
            print(f"Executing batch {i//self.batch_size + 1}/{(len(tests) + self.batch_size - 1)//self.batch_size}")
            
            batch_results = await self.execution_engine.execute_parallel(
                batch, max_parallel, fail_fast
            )
            
            all_results.extend(batch_results)
            
            # Stop if fail_fast and we have failures
            if fail_fast and any(r["status"] == "failed" for r in batch_results):
                break
        
        return all_results


class TestCommandBuilder:
    """Builds test execution commands for different test types"""
    
    @staticmethod
    def build_pytest_command(
        test_path: str, 
        markers: str = None,
        timeout: int = 300,
        parallel: bool = False,
        verbose: bool = True
    ) -> List[str]:
        """Build pytest command"""
        cmd = [sys.executable, "-m", "pytest"]
        
        if test_path:
            cmd.append(test_path)
        
        if markers:
            cmd.extend(["-m", markers])
        
        if timeout:
            cmd.extend(["--timeout", str(timeout)])
        
        if parallel:
            cmd.extend(["-n", "auto"])
        
        if verbose:
            cmd.extend(["-v", "--tb=short"])
        else:
            cmd.extend(["-q", "--tb=no"])
        
        return cmd
    
    @staticmethod
    def build_jest_command(
        test_path: str = None,
        coverage: bool = False,
        silent: bool = False
    ) -> List[str]:
        """Build Jest command"""
        cmd = ["npm", "test"]
        
        if silent:
            cmd.append("--silent")
        
        if coverage:
            cmd.append("--coverage")
        
        if test_path:
            cmd.extend(["--", test_path])
        
        return cmd
    
    @staticmethod
    def build_cypress_command(
        test_path: str = None,
        headless: bool = True,
        browser: str = "chrome"
    ) -> List[str]:
        """Build Cypress command"""
        cmd = ["npx", "cypress"]
        
        if headless:
            cmd.append("run")
        else:
            cmd.append("open")
        
        if browser:
            cmd.extend(["--browser", browser])
        
        if test_path:
            cmd.extend(["--spec", test_path])
        
        return cmd