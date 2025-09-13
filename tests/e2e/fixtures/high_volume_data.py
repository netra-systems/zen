"""

High Volume Test Data Generators and Fixtures



Provides test data generation and fixtures for high-volume throughput testing.



Business Value Justification (BVJ):

- Segment: Enterprise/Mid

- Business Goal: Test Data Management, Performance Validation

- Value Impact: Ensures realistic test scenarios for enterprise workloads

- Strategic Impact: Supports thorough performance validation

"""



import asyncio

import json

import logging

import random

import time

import uuid

from typing import Any, Dict, List, Optional



import httpx

import pytest



logger = logging.getLogger(__name__)



# Environment configuration

E2E_TEST_CONFIG = {

    "websocket_url": "ws://localhost:8765",

    "backend_url": "http://localhost:8000", 

    "auth_service_url": "http://localhost:8081",

    "skip_real_services": True,

    "test_mode": "mock"

}





class HighVolumeDataGenerator:

    """Generates test data for high-volume scenarios."""

    

    @staticmethod

    def generate_message_batch(count: int, client_id: str, 

                             message_type: str = "user_message") -> List[Dict]:

        """Generate batch of test messages."""

        messages = []

        for i in range(count):

            message = {

                "type": message_type,

                "message_id": f"{client_id}-{i}-{uuid.uuid4().hex[:8]}",

                "client_id": client_id,

                "sequence_id": i,

                "timestamp": time.time(),

                "payload": {

                    "content": f"Test message {i} from {client_id}",

                    "size_bytes": 1024,  # 1KB message

                    "priority": "normal"

                }

            }

            messages.append(message)

        return messages

    

    @staticmethod

    def generate_throughput_test_message(message_id: str, client_id: str) -> Dict:

        """Generate optimized throughput test message."""

        return {

            "type": "throughput_test",

            "message_id": message_id,

            "client_id": client_id,

            "send_time": time.time(),

            "payload_size": random.randint(100, 2048),  # Variable payload

            "echo_request": True

        }

    

    @staticmethod

    def generate_latency_probe_message(probe_id: str, client_id: str) -> Dict:

        """Generate latency measurement probe."""

        return {

            "type": "latency_probe", 

            "probe_id": probe_id,

            "client_id": client_id,

            "send_timestamp": time.time(),

            "probe_size": 64,  # Small probe for latency measurement

            "expect_echo": True

        }

    

    @staticmethod

    def generate_burst_pattern_data(rate: int, duration: int) -> List[Dict]:

        """Generate burst pattern test data."""

        total_messages = rate * duration

        burst_data = []

        

        for i in range(total_messages):

            timestamp = time.time() + (i / rate)  # Spread over duration

            message = {

                "type": "burst_test",

                "message_id": f"burst-{i}-{uuid.uuid4().hex[:8]}",

                "scheduled_time": timestamp,

                "burst_rate": rate,

                "sequence": i,

                "total_in_burst": total_messages

            }

            burst_data.append(message)

        

        return burst_data

    

    @staticmethod

    def generate_scaling_test_data(scaling_steps: List[int]) -> Dict[int, List[Dict]]:

        """Generate data for scaling tests."""

        scaling_data = {}

        

        for step in scaling_steps:

            messages = []

            for i in range(step * 10):  # 10 messages per connection

                message = {

                    "type": "scaling_test",

                    "message_id": f"scale-{step}-{i}-{uuid.uuid4().hex[:8]}",

                    "connection_count": step,

                    "message_index": i,

                    "test_phase": f"scaling_{step}"

                }

                messages.append(message)

            scaling_data[step] = messages

        

        return scaling_data





class MockAuthenticator:

    """Mock authentication for testing."""

    

    @staticmethod

    def generate_test_token(user_id: str) -> str:

        """Generate mock JWT token."""

        return f"mock-jwt-{user_id}-{uuid.uuid4().hex}"

    

    @staticmethod

    def create_test_user() -> Dict[str, str]:

        """Create mock test user."""

        user_id = f"throughput-user-{uuid.uuid4().hex[:8]}"

        return {

            "user_id": user_id,

            "token": MockAuthenticator.generate_test_token(user_id),

            "email": f"{user_id}@example.com"

        }





# Pytest Fixtures



@pytest.fixture

async def test_user_token():

    """Create test user and return auth token."""

    if E2E_TEST_CONFIG["test_mode"] == "real":

        # Use real authentication service - fail if not available

        async with httpx.AsyncClient(follow_redirects=True) as client:

            response = await client.post(

                f"{E2E_TEST_CONFIG['auth_service_url']}/auth/test-user",

                json={"email": f"throughput-test-{uuid.uuid4().hex[:8]}@example.com"},

                timeout=10.0

            )

            if response.status_code != 200:

                raise RuntimeError(f"Authentication service returned {response.status_code}")

            

            token_data = response.json()

            return {

                "user_id": token_data["user_id"],

                "token": token_data["token"],

                "email": token_data["email"]

            }

    

    # No fallback - authentication service must be available

    raise RuntimeError("Authentication service not configured for E2E tests")





@pytest.fixture

def high_volume_data_generator():

    """Provide high volume data generator."""

    return HighVolumeDataGenerator()





@pytest.fixture

def burst_test_data(high_volume_data_generator):

    """Generate burst test data."""

    return high_volume_data_generator.generate_burst_pattern_data(rate=1000, duration=30)





@pytest.fixture

def scaling_test_data(high_volume_data_generator):

    """Generate scaling test data."""

    scaling_steps = [1, 10, 50, 100, 250, 500]

    return high_volume_data_generator.generate_scaling_test_data(scaling_steps)





@pytest.fixture

def latency_probe_data(high_volume_data_generator):

    """Generate latency probe data."""

    probes = []

    for i in range(100):  # 100 latency probes

        probe = high_volume_data_generator.generate_latency_probe_message(

            f"probe-{i}", "latency-client"

        )

        probes.append(probe)

    return probes

