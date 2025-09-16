"""
Test Resource Limits

Validates CPU, memory, and other resource limits
are enforced in the staging environment.
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import pytest
# Test framework import - using pytest fixtures instead

import asyncio
import os
import time
from typing import Dict, List

import httpx
import psutil

from netra_backend.tests.integration.staging_config.base import StagingConfigTestBase

class TestResourceLimits(StagingConfigTestBase):
    """Test resource limits in staging."""

    @pytest.mark.asyncio
    async def test_memory_limits(self):
        """Test memory limit enforcement."""
        self.skip_if_not_staging()

        async with httpx.AsyncClient() as client:
            # Try to allocate large amount of memory
            response = await client.post(
            f"{self.staging_url}/api/debug/allocate-memory",
            json={
            'size_mb': 1000  # Try to allocate 1GB
            },
            headers={
            'Authorization': 'Bearer admin_token'
            },
            timeout=10.0
            )

            # Should either succeed with limit info or reject
            if response.status_code == 200:
                data = response.json()
                self.assertIn('memory_limit', data,
                "Should report memory limit")
                self.assertLess(data.get('allocated', 0), 2000,
                "Should not allocate unlimited memory")
            elif response.status_code in [403, 404]:
                # Debug endpoint might not exist or require auth
                pass
            else:
                self.assertEqual(response.status_code, 507,
                "Should return 507 if memory limit exceeded")

                @pytest.mark.asyncio
                async def test_cpu_limits(self):
                    """Test CPU limit enforcement."""
                    self.skip_if_not_staging()

                    async with httpx.AsyncClient() as client:
            # Try CPU-intensive operation
                        response = await client.post(
                        f"{self.staging_url}/api/debug/cpu-intensive",
                        json={
                        'duration_seconds': 5
                        },
                        headers={
                        'Authorization': 'Bearer admin_token'
                        },
                        timeout=10.0
                        )

                        if response.status_code == 200:
                            data = response.json()
                # Check if CPU was throttled
                            if 'cpu_throttled' in data:
                                self.assertLess(data.get('cpu_usage_percent', 100), 100,
                                "CPU should be throttled")

                                @pytest.mark.asyncio
                                async def test_connection_limits(self):
                                    """Test connection limit enforcement."""
                                    self.skip_if_not_staging()

                                    max_connections = 100
                                    connections = []
                                    successful = 0
                                    rejected = 0

                                    async with httpx.AsyncClient() as client:
                                        for i in range(max_connections):
                                            try:
                                                response = await client.get(
                                                f"{self.staging_url}/health",
                                                timeout=2.0
                                                )
                                                if response.status_code == 200:
                                                    successful += 1
                                                elif response.status_code == 503:
                                                    rejected += 1
                                                    break
                                            except:
                                                rejected += 1

        # Should enforce connection limits
                                                if rejected > 0:
                                                    self.assertLess(successful, max_connections,
                                                    "Connection limit should be enforced")

                                                    @pytest.mark.asyncio
                                                    async def test_request_rate_limits(self):
                                                        """Test request rate limiting."""
                                                        self.skip_if_not_staging()

                                                        async with httpx.AsyncClient() as client:
            # Make rapid requests
                                                            start_time = time.time()
                                                            responses = []

                                                            for i in range(50):
                                                                response = await client.get(
                                                                f"{self.staging_url}/api/threads",
                                                                headers={
                                                                'Authorization': 'Bearer test_token'
                                                                },
                                                                timeout=5.0
                                                                )
                                                                responses.append(response.status_code)

                                                                if response.status_code == 429:
                                                                    break

                                                                elapsed = time.time() - start_time

            # Check if rate limiting kicked in
                                                                rate_limited = any(status == 429 for status in responses)

                                                                if rate_limited:
                # Verify rate limit headers
                                                                    for i, status in enumerate(responses):
                                                                        if status == 429:
                                                                            self.assertLess(i, 50,
                                                                            "Rate limit should trigger before 50 requests")
                                                                            break

                                                                        @pytest.mark.asyncio
                                                                        async def test_payload_size_limits(self):
                                                                            """Test request payload size limits."""
                                                                            self.skip_if_not_staging()

        # Create large payload
                                                                            large_payload = {
                                                                            'data': 'x' * (10 * 1024 * 1024)  # 10MB
                                                                            }

                                                                            async with httpx.AsyncClient() as client:
                                                                                response = await client.post(
                                                                                f"{self.staging_url}/api/threads",
                                                                                json=large_payload,
                                                                                headers={
                                                                                'Authorization': 'Bearer test_token'
                                                                                },
                                                                                timeout=10.0
                                                                                )

            # Should reject large payloads
                                                                                self.assertIn(response.status_code, [413, 400],
                                                                                "Should reject oversized payload")

                                                                                @pytest.mark.asyncio
                                                                                async def test_file_upload_limits(self):
                                                                                    """Test file upload size limits."""
                                                                                    self.skip_if_not_staging()

        # Create large file content
                                                                                    file_content = b'x' * (50 * 1024 * 1024)  # 50MB

                                                                                    async with httpx.AsyncClient() as client:
                                                                                        files = {'file': ('large.bin', file_content, 'application/octet-stream')}

                                                                                        response = await client.post(
                                                                                        f"{self.staging_url}/api/upload",
                                                                                        files=files,
                                                                                        headers={
                                                                                        'Authorization': 'Bearer test_token'
                                                                                        },
                                                                                        timeout=30.0
                                                                                        )

            # Should enforce file size limits
                                                                                        self.assertIn(response.status_code, [413, 400, 404],
                                                                                        "Should enforce file upload limits")

                                                                                        @pytest.mark.asyncio
                                                                                        async def test_timeout_enforcement(self):
                                                                                            """Test request timeout enforcement."""
                                                                                            self.skip_if_not_staging()

                                                                                            async with httpx.AsyncClient() as client:
            # Request long-running operation
                                                                                                response = await client.post(
                                                                                                f"{self.staging_url}/api/debug/sleep",
                                                                                                json={
                                                                                                'duration_seconds': 120  # 2 minutes
                                                                                                },
                                                                                                headers={
                                                                                                'Authorization': 'Bearer admin_token'
                                                                                                },
                                                                                                timeout=10.0
                                                                                                )

            # Should timeout or reject
                                                                                                if response.status_code != 404:
                                                                                                    self.assertIn(response.status_code, [408, 504],
                                                                                                    "Long requests should timeout")

                                                                                                    @pytest.mark.asyncio
                                                                                                    async def test_disk_space_limits(self):
                                                                                                        """Test disk space limit enforcement."""
                                                                                                        self.skip_if_not_staging()

                                                                                                        async with httpx.AsyncClient() as client:
            # Check available disk space
                                                                                                            response = await client.get(
                                                                                                            f"{self.staging_url}/api/system/disk",
                                                                                                            headers={
                                                                                                            'Authorization': 'Bearer admin_token'
                                                                                                            },
                                                                                                            timeout=5.0
                                                                                                            )

                                                                                                            if response.status_code == 200:
                                                                                                                data = response.json()

                # Verify disk limits are configured
                                                                                                                self.assertIn('total_bytes', data)
                                                                                                                self.assertIn('used_bytes', data)
                                                                                                                self.assertIn('available_bytes', data)

                # Check if disk usage is monitored
                                                                                                                usage_percent = (data['used_bytes'] / data['total_bytes']) * 100
                                                                                                                self.assertLess(usage_percent, 90,
                                                                                                                "Disk usage should be below 90%")

                                                                                                                @pytest.mark.asyncio
                                                                                                                async def test_database_connection_pool(self):
                                                                                                                    """Test database connection pool limits."""
                                                                                                                    self.skip_if_not_staging()

                                                                                                                    async with httpx.AsyncClient() as client:
            # Get connection pool metrics
                                                                                                                        response = await client.get(
                                                                                                                        f"{self.staging_url}/metrics",
                                                                                                                        timeout=5.0
                                                                                                                        )

                                                                                                                        metrics_text = response.text

            # Check for connection pool metrics
                                                                                                                        pool_metrics = [
                                                                                                                        'database_pool_size',
                                                                                                                        'database_pool_overflow',
                                                                                                                        'database_pool_checked_out'
                                                                                                                        ]

                                                                                                                        for metric in pool_metrics:
                                                                                                                            if metric in metrics_text:
                    # Extract value
                                                                                                                                for line in metrics_text.split('\n'):
                                                                                                                                    if metric in line and not line.startswith('#'):
                            # Parse value
                                                                                                                                        import re
                                                                                                                                        match = re.search(r'(\d+)$', line)
                                                                                                                                        if match:
                                                                                                                                            value = int(match.group(1))

                                # Verify reasonable limits
                                                                                                                                            if 'pool_size' in metric:
                                                                                                                                                self.assertLessEqual(value, 100,
                                                                                                                                                "Pool size should be limited")
                                                                                                                                            elif 'overflow' in metric:
                                                                                                                                                self.assertLessEqual(value, 10,
                                                                                                                                                "Overflow should be limited")