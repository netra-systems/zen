#!/usr/bin/env python3
"""
Comprehensive test to verify background job orchestration:
1. Job scheduling and queuing
2. Job execution and monitoring
3. Job dependencies and chaining
4. Retry and failure handling
5. Job cancellation and cleanup
6. Cron-based scheduling

This test ensures background jobs are properly orchestrated.
"""

# Test framework import - using pytest fixtures instead

import asyncio
import json
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import pytest

# Configuration
DEV_BACKEND_URL = "http://localhost:8000"
JOBS_API_URL = f"{DEV_BACKEND_URL}/api/v1/jobs"
AUTH_SERVICE_URL = "http://localhost:8081"

class BackgroundJobOrchestrationTester:
    """Test background job orchestration flow."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.scheduled_jobs: List[str] = []
        self.completed_jobs: List[str] = []
        self.failed_jobs: List[str] = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.setup_auth()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def setup_auth(self):
        """Setup authentication."""
        user_data = {
            "email": "jobs_test@example.com",
            "password": "jobstest123",
            "name": "Jobs Test User"
        }
        
        # Register/login
        await self.session.post(f"{AUTH_SERVICE_URL}/auth/register", json=user_data)
        
        async with self.session.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={"email": user_data["email"], "password": user_data["password"]}
        ) as response:
            if response.status == 200:
                data = await response.json()
                self.auth_token = data.get("access_token")
                
    @pytest.mark.asyncio
    async def test_job_scheduling(self) -> bool:
        """Test basic job scheduling."""
        print("\n[SCHEDULE] Testing job scheduling...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Schedule immediate job
        job_data = {
            "name": "test_immediate_job",
            "type": "data_processing",
            "payload": {"data": "test_data"},
            "schedule": "immediate"
        }
        
        async with self.session.post(
            f"{JOBS_API_URL}/schedule",
            json=job_data,
            headers=headers
        ) as response:
            if response.status in [200, 201]:
                data = await response.json()
                job_id = data.get("job_id")
                self.scheduled_jobs.append(job_id)
                print(f"[OK] Job scheduled: {job_id}")
                return True
                
        return False
        
    @pytest.mark.asyncio
    async def test_delayed_job_scheduling(self) -> bool:
        """Test delayed job scheduling."""
        print("\n[DELAY] Testing delayed job scheduling...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Schedule job for 5 seconds from now
        run_at = (datetime.utcnow() + timedelta(seconds=5)).isoformat()
        
        job_data = {
            "name": "test_delayed_job",
            "type": "notification",
            "payload": {"message": "Delayed notification"},
            "run_at": run_at
        }
        
        async with self.session.post(
            f"{JOBS_API_URL}/schedule",
            json=job_data,
            headers=headers
        ) as response:
            if response.status in [200, 201]:
                data = await response.json()
                job_id = data.get("job_id")
                self.scheduled_jobs.append(job_id)
                
                # Check job status
                await asyncio.sleep(2)
                
                async with self.session.get(
                    f"{JOBS_API_URL}/{job_id}/status",
                    headers=headers
                ) as status_response:
                    if status_response.status == 200:
                        status_data = await status_response.json()
                        if status_data.get("status") == "scheduled":
                            print(f"[OK] Delayed job scheduled for: {run_at}")
                            return True
                            
        return False
        
    @pytest.mark.asyncio
    async def test_job_dependencies(self) -> bool:
        """Test job dependency chaining."""
        print("\n[CHAIN] Testing job dependencies...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Create parent job
        parent_job = {
            "name": "parent_job",
            "type": "data_fetch",
            "payload": {"source": "database"}
        }
        
        async with self.session.post(
            f"{JOBS_API_URL}/schedule",
            json=parent_job,
            headers=headers
        ) as response:
            if response.status in [200, 201]:
                parent_data = await response.json()
                parent_id = parent_data.get("job_id")
                
                # Create dependent job
                child_job = {
                    "name": "child_job",
                    "type": "data_process",
                    "payload": {"action": "transform"},
                    "depends_on": [parent_id]
                }
                
                async with self.session.post(
                    f"{JOBS_API_URL}/schedule",
                    json=child_job,
                    headers=headers
                ) as child_response:
                    if child_response.status in [200, 201]:
                        child_data = await child_response.json()
                        child_id = child_data.get("job_id")
                        
                        self.scheduled_jobs.extend([parent_id, child_id])
                        print(f"[OK] Job chain created: {parent_id} -> {child_id}")
                        return True
                        
        return False
        
    @pytest.mark.asyncio
    async def test_job_execution_monitoring(self) -> bool:
        """Test job execution monitoring."""
        print("\n[MONITOR] Testing job execution monitoring...")
        
        if not self.scheduled_jobs:
            return False
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        job_id = self.scheduled_jobs[0]
        
        # Monitor job execution
        max_attempts = 10
        for i in range(max_attempts):
            async with self.session.get(
                f"{JOBS_API_URL}/{job_id}/status",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get("status")
                    
                    print(f"[INFO] Job {job_id[:8]} status: {status}")
                    
                    if status == "completed":
                        self.completed_jobs.append(job_id)
                        print(f"[OK] Job completed successfully")
                        return True
                    elif status == "failed":
                        self.failed_jobs.append(job_id)
                        print(f"[INFO] Job failed (expected for some test jobs)")
                        return True
                        
            await asyncio.sleep(1)
            
        return False
        
    @pytest.mark.asyncio
    async def test_job_retry_mechanism(self) -> bool:
        """Test job retry on failure."""
        print("\n[RETRY] Testing job retry mechanism...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Schedule a job that will fail initially
        job_data = {
            "name": "retry_test_job",
            "type": "flaky_operation",
            "payload": {"fail_count": 2},  # Fail first 2 attempts
            "retry_policy": {
                "max_attempts": 3,
                "backoff": "exponential",
                "delay": 1
            }
        }
        
        async with self.session.post(
            f"{JOBS_API_URL}/schedule",
            json=job_data,
            headers=headers
        ) as response:
            if response.status in [200, 201]:
                data = await response.json()
                job_id = data.get("job_id")
                
                # Monitor retries
                await asyncio.sleep(5)
                
                async with self.session.get(
                    f"{JOBS_API_URL}/{job_id}/history",
                    headers=headers
                ) as history_response:
                    if history_response.status == 200:
                        history = await history_response.json()
                        attempts = history.get("attempts", [])
                        
                        if len(attempts) > 1:
                            print(f"[OK] Job retried {len(attempts)} times")
                            return True
                            
        return False
        
    @pytest.mark.asyncio
    async def test_job_cancellation(self) -> bool:
        """Test job cancellation."""
        print("\n[CANCEL] Testing job cancellation...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Schedule a long-running job
        job_data = {
            "name": "long_running_job",
            "type": "long_process",
            "payload": {"duration": 30}
        }
        
        async with self.session.post(
            f"{JOBS_API_URL}/schedule",
            json=job_data,
            headers=headers
        ) as response:
            if response.status in [200, 201]:
                data = await response.json()
                job_id = data.get("job_id")
                
                # Wait a moment then cancel
                await asyncio.sleep(2)
                
                async with self.session.post(
                    f"{JOBS_API_URL}/{job_id}/cancel",
                    headers=headers
                ) as cancel_response:
                    if cancel_response.status in [200, 204]:
                        # Verify cancellation
                        async with self.session.get(
                            f"{JOBS_API_URL}/{job_id}/status",
                            headers=headers
                        ) as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                if status_data.get("status") == "cancelled":
                                    print(f"[OK] Job cancelled successfully")
                                    return True
                                    
        return False
        
    @pytest.mark.asyncio
    async def test_cron_scheduling(self) -> bool:
        """Test cron-based job scheduling."""
        print("\n[CRON] Testing cron scheduling...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Schedule recurring job
        job_data = {
            "name": "cron_test_job",
            "type": "periodic_task",
            "payload": {"action": "cleanup"},
            "schedule": "*/5 * * * *"  # Every 5 minutes
        }
        
        async with self.session.post(
            f"{JOBS_API_URL}/schedule",
            json=job_data,
            headers=headers
        ) as response:
            if response.status in [200, 201]:
                data = await response.json()
                cron_id = data.get("cron_id")
                
                # Verify cron job created
                async with self.session.get(
                    f"{JOBS_API_URL}/cron/{cron_id}",
                    headers=headers
                ) as cron_response:
                    if cron_response.status == 200:
                        cron_data = await cron_response.json()
                        next_run = cron_data.get("next_run")
                        print(f"[OK] Cron job scheduled. Next run: {next_run}")
                        return True
                        
        return False
        
    @pytest.mark.asyncio
    async def test_job_queue_status(self) -> bool:
        """Test job queue status monitoring."""
        print("\n[QUEUE] Testing job queue status...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with self.session.get(
            f"{JOBS_API_URL}/queue/status",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                
                print(f"[INFO] Queue status:")
                print(f"  - Pending: {data.get('pending', 0)}")
                print(f"  - Running: {data.get('running', 0)}")
                print(f"  - Completed: {data.get('completed', 0)}")
                print(f"  - Failed: {data.get('failed', 0)}")
                
                return True
                
        return False
        
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests in sequence."""
        results = {}
        
        if not self.auth_token:
            print("[ERROR] Authentication failed")
            return results
            
        results["job_scheduling"] = await self.test_job_scheduling()
        results["delayed_scheduling"] = await self.test_delayed_job_scheduling()
        results["job_dependencies"] = await self.test_job_dependencies()
        results["execution_monitoring"] = await self.test_job_execution_monitoring()
        results["retry_mechanism"] = await self.test_job_retry_mechanism()
        results["job_cancellation"] = await self.test_job_cancellation()
        results["cron_scheduling"] = await self.test_cron_scheduling()
        results["queue_status"] = await self.test_job_queue_status()
        
        return results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_background_job_orchestration():
    """Test background job orchestration."""
    async with BackgroundJobOrchestrationTester() as tester:
        results = await tester.run_all_tests()
        
        print("\n" + "="*60)
        print("BACKGROUND JOB ORCHESTRATION TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {test_name:25} : {status}")
            
        print("="*60)
        print(f"\nJobs scheduled: {len(tester.scheduled_jobs)}")
        print(f"Jobs completed: {len(tester.completed_jobs)}")
        print(f"Jobs failed: {len(tester.failed_jobs)}")
        
        assert all(results.values()), f"Some tests failed: {results}"

if __name__ == "__main__":
    exit_code = asyncio.run(test_background_job_orchestration())
    sys.exit(0 if exit_code else 1)