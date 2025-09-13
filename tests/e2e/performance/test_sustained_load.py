"""

Sustained Load and Backpressure Tests



Tests sustained load handling, backpressure mechanisms, and system recovery.



Business Value Justification (BVJ):

- Segment: Enterprise/Mid

- Business Goal: Platform Stability, Queue Management

- Value Impact: Prevents system overload and ensures graceful degradation

- Strategic Impact: Critical for production stability under sustained high load

"""



import asyncio

import json

import logging

import time

from shared.isolated_environment import IsolatedEnvironment



import pytest



from tests.e2e.test_helpers.performance_base import (

    HIGH_VOLUME_CONFIG,

    LoadTestResults,

    ThroughputAnalyzer,

)



logger = logging.getLogger(__name__)





class TestBackpressureMechanismTesting:

    """Test backpressure and queue overflow protection."""

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    @pytest.mark.timeout(180)

    async def test_backpressure_mechanism_testing(self, throughput_client, high_volume_server):

        """Validate queue overflow protection and backpressure signaling."""

        test_results = self._create_test_results("backpressure_mechanism_testing")

        

        logger.info("Testing backpressure mechanisms with queue overflow...")

        

        # Phase 1: Establish baseline

        baseline_metrics = await self._establish_baseline(throughput_client)

        

        # Phase 2: Trigger backpressure

        backpressure_data = await self._test_backpressure_overflow(throughput_client)

        

        # Phase 3: Test priority preservation

        priority_data = await self._test_priority_preservation(throughput_client)

        

        # Phase 4: Test recovery

        recovery_data = await self._test_queue_recovery(throughput_client)

        

        self._assert_backpressure_requirements(backpressure_data, priority_data, recovery_data)

        self._finalize_backpressure_results(test_results, baseline_metrics, backpressure_data)

        

        logger.info("Backpressure mechanism testing completed successfully")



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_sustained_load_handling(self, throughput_client, high_volume_server):

        """Test sustained load handling over extended periods."""

        logger.info("Testing sustained load handling...")

        

        duration = HIGH_VOLUME_CONFIG["sustained_load_time"]  # 30 seconds

        target_rate = HIGH_VOLUME_CONFIG["sustained_throughput_target"]  # 5000 msg/sec

        

        start_time = time.time()

        total_sent = 0

        total_received = 0

        throughput_samples = []

        

        # Send sustained load for specified duration

        while time.time() - start_time < duration:

            batch_size = min(1000, int(target_rate))  # 1 second batches

            

            batch_start = time.perf_counter()

            results = await throughput_client.send_throughput_burst(

                message_count=batch_size, rate_limit=target_rate

            )

            

            responses = await throughput_client.receive_responses(

                expected_count=batch_size, timeout=5.0

            )

            batch_duration = time.perf_counter() - batch_start

            

            sent_count = len([r for r in results if r["status"] == "sent"])

            received_count = len(responses)

            

            total_sent += sent_count

            total_received += received_count

            

            batch_throughput = sent_count / batch_duration if batch_duration > 0 else 0

            throughput_samples.append(batch_throughput)

            

            # Brief pause between batches

            await asyncio.sleep(0.1)

        

        self._assert_sustained_load_performance(throughput_samples, total_sent, total_received)



    def _create_test_results(self, test_name: str) -> LoadTestResults:

        """Create test results object."""

        return LoadTestResults(

            test_name=test_name,

            start_time=time.time(),

            end_time=0,

            total_duration=0

        )

    

    async def _establish_baseline(self, client) -> dict:

        """Establish baseline performance."""

        baseline_count = 1000

        results = await client.send_throughput_burst(

            message_count=baseline_count, rate_limit=500

        )

        responses = await client.receive_responses(baseline_count, timeout=30.0)

        

        return {

            "sent": len([r for r in results if r["status"] == "sent"]),

            "received": len(responses),

            "rate": len(responses) / 30.0

        }

    

    async def _test_backpressure_overflow(self, client) -> dict:

        """Test backpressure triggering under overflow."""

        overflow_count = 15000

        backpressure_signals = []

        

        logger.info(f"Sending {overflow_count} messages to trigger backpressure...")

        

        start_time = time.perf_counter()

        results = await client.send_throughput_burst(

            message_count=overflow_count, rate_limit=None

        )

        send_duration = time.perf_counter() - start_time

        

        # Monitor for backpressure signals

        responses = await self._monitor_backpressure_signals(client, 60.0)

        backpressure_signals = [r for r in responses if r.get("type") == "backpressure"]

        

        return {

            "overflow_sent": len([r for r in results if r["status"] == "sent"]),

            "send_duration": send_duration,

            "backpressure_signals": len(backpressure_signals),

            "responses": len(responses)

        }

    

    async def _test_priority_preservation(self, client) -> dict:

        """Test priority message preservation during overflow."""

        logger.info("Testing priority message preservation...")

        

        priority_messages = []

        priority_responses = []

        

        for i in range(10):

            message = {

                "type": "user_message",

                "message_id": f"priority-{i}",

                "content": f"High priority message {i}",

                "priority": "high",

                "timestamp": time.time()

            }

            

            try:

                await client.connection.send(json.dumps(message))

                priority_messages.append(message)

                

                response = await asyncio.wait_for(

                    client.connection.recv(), timeout=5.0

                )

                priority_responses.append(json.loads(response))

                

            except Exception as e:

                logger.warning(f"Priority message {i} error: {e}")

        

        return {

            "sent": len(priority_messages),

            "received": len(priority_responses)

        }

    

    async def _test_queue_recovery(self, client) -> dict:

        """Test queue recovery after load reduction."""

        logger.info("Testing queue recovery...")

        

        recovery_start = time.time()

        queue_recovered = False

        

        # Wait for queue to drain

        while time.time() - recovery_start < HIGH_VOLUME_CONFIG["queue_recovery_timeout"]:

            stats = await client.get_performance_stats()

            if isinstance(stats, dict) and stats.get("queue_depth", float('inf')) < 100:

                queue_recovered = True

                break

            await asyncio.sleep(1.0)

        

        # Test operation after recovery

        recovery_data = {"recovered": queue_recovered}

        

        if queue_recovered:

            results = await client.send_throughput_burst(

                message_count=500, rate_limit=300

            )

            responses = await client.receive_responses(500, timeout=20.0)

            

            recovery_data.update({

                "post_recovery_sent": len([r for r in results if r["status"] == "sent"]),

                "post_recovery_received": len(responses)

            })

        

        return recovery_data

    

    async def _monitor_backpressure_signals(self, client, timeout: float) -> list:

        """Monitor for backpressure signals."""

        responses = []

        start_time = time.time()

        

        while time.time() - start_time < timeout:

            try:

                response = await asyncio.wait_for(

                    client.connection.recv(), timeout=1.0

                )

                response_data = json.loads(response)

                responses.append(response_data)

                

            except asyncio.TimeoutError:

                continue

            except Exception as e:

                logger.warning(f"Error monitoring backpressure: {e}")

                break

        

        return responses

    

    def _assert_backpressure_requirements(self, backpressure_data: dict, 

                                        priority_data: dict, recovery_data: dict):

        """Assert backpressure mechanism requirements."""

        # Should detect overflow and send backpressure signals

        assert backpressure_data["backpressure_signals"] > 0, \

            "No backpressure signals detected during overflow"

        

        # Priority messages should still be processed

        priority_ratio = priority_data["received"] / priority_data["sent"] \

            if priority_data["sent"] > 0 else 0

        assert priority_ratio >= 0.8, \

            f"Priority message processing too low: {priority_ratio:.3f}"

        

        # System should recover after load reduction

        assert recovery_data["recovered"], "Queue did not recover within timeout"

        

        if "post_recovery_sent" in recovery_data:

            recovery_ratio = recovery_data["post_recovery_received"] / \

                           recovery_data["post_recovery_sent"]

            assert recovery_ratio >= 0.95, \

                f"Post-recovery performance too low: {recovery_ratio:.3f}"

    

    def _assert_sustained_load_performance(self, throughput_samples: list, 

                                         total_sent: int, total_received: int):

        """Assert sustained load performance requirements."""

        # Overall delivery ratio

        delivery_ratio = total_received / total_sent if total_sent > 0 else 0

        assert delivery_ratio >= 0.95, \

            f"Sustained load delivery ratio too low: {delivery_ratio:.3f}"

        

        # Throughput consistency

        if throughput_samples:

            avg_throughput = sum(throughput_samples) / len(throughput_samples)

            min_throughput = min(throughput_samples)

            consistency_ratio = min_throughput / avg_throughput if avg_throughput > 0 else 0

            

            assert consistency_ratio >= 0.8, \

                f"Throughput inconsistency too high: {consistency_ratio:.3f}"

    

    def _finalize_backpressure_results(self, test_results: LoadTestResults, 

                                     baseline_metrics: dict, backpressure_data: dict):

        """Finalize test results."""

        test_results.messages_sent = baseline_metrics["sent"] + backpressure_data["overflow_sent"]

        test_results.messages_received = baseline_metrics["received"] + backpressure_data["responses"]

        test_results.backpressure_events = backpressure_data["backpressure_signals"]

        test_results.delivery_ratio = test_results.messages_received / test_results.messages_sent

        test_results.end_time = time.time()

        test_results.total_duration = test_results.end_time - test_results.start_time

