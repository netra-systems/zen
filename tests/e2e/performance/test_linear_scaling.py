"""

Linear Throughput Scaling Tests



Tests linear scaling characteristics and system performance limits.



Business Value Justification (BVJ):

- Segment: Enterprise/Mid

- Business Goal: Platform Stability, Scalability Validation  

- Value Impact: Ensures predictable performance scaling for enterprise workloads

- Strategic Impact: Critical for enterprise SLAs and capacity planning

"""



import asyncio

import logging

import statistics

import time

from shared.isolated_environment import IsolatedEnvironment



import pytest



from tests.e2e.test_helpers.performance_base import (

    HIGH_VOLUME_CONFIG,

    LoadTestResults,

    ThroughputAnalyzer,

)



logger = logging.getLogger(__name__)





class TestLinearThroughputScaling:

    """Test linear throughput scaling characteristics."""

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    @pytest.mark.timeout(300)

    async def test_linear_throughput_scaling(self, throughput_client, high_volume_server):

        """Validate system performance scales linearly with increasing message rates."""

        test_results = self._create_test_results("linear_throughput_scaling")

        scaling_results = {}

        

        for rate in HIGH_VOLUME_CONFIG["message_rate_scaling_steps"]:

            logger.info(f"Testing throughput at {rate} msg/sec...")

            

            message_count = rate * 30  # 30 seconds worth

            start_time = time.perf_counter()

            

            results = await throughput_client.send_throughput_burst(

                message_count=message_count, rate_limit=rate

            )

            send_duration = time.perf_counter() - start_time

            

            responses = await throughput_client.receive_responses(

                expected_count=message_count, timeout=60.0

            )

            

            metrics = self._calculate_rate_metrics(results, responses, send_duration)

            scaling_results[rate] = metrics

            test_results.rate_scaling_data[rate] = ThroughputAnalyzer.calculate_throughput_metrics(

                metrics["sent_count"], metrics["received_count"], send_duration

            )

            

            self._assert_rate_performance(rate, metrics)

            await asyncio.sleep(2.0)  # Stabilize between tests

        

        self._validate_scaling_linearity(scaling_results)

        self._finalize_test_results(test_results, scaling_results)

        

        logger.info(f"Linear scaling test completed: Peak {test_results.peak_throughput:.1f} msg/sec")



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_concurrent_connection_scaling(self, high_volume_server):

        """Test throughput scaling with increasing concurrent connections."""

        scaling_results = {}

        

        for conn_count in HIGH_VOLUME_CONFIG["connection_scaling_steps"]:

            logger.info(f"Testing {conn_count} concurrent connections...")

            

            clients = await self._create_multiple_clients(conn_count)

            

            try:

                start_time = time.perf_counter()

                tasks = [self._run_client_burst(client, 100) for client in clients]

                results = await asyncio.gather(*tasks)

                duration = time.perf_counter() - start_time

                

                total_sent = sum(r["sent_count"] for r in results)

                total_received = sum(r["received_count"] for r in results)

                

                scaling_results[conn_count] = {

                    "connection_count": conn_count,

                    "total_sent": total_sent,

                    "total_received": total_received,

                    "duration": duration,

                    "throughput": total_sent / duration if duration > 0 else 0

                }

                

                assert total_received >= total_sent * 0.95, \

                    f"Too many dropped messages with {conn_count} connections"

                

            finally:

                await self._cleanup_clients(clients)

        

        self._validate_connection_scaling(scaling_results)



    def _create_test_results(self, test_name: str) -> LoadTestResults:

        """Create test results object."""

        return LoadTestResults(

            test_name=test_name,

            start_time=time.time(),

            end_time=0,

            total_duration=0

        )

    

    def _calculate_rate_metrics(self, results: list, responses: list, duration: float) -> dict:

        """Calculate metrics for a specific rate test."""

        sent_count = len([r for r in results if r["status"] == "sent"])

        received_count = len(responses)

        actual_send_rate = sent_count / duration if duration > 0 else 0

        

        return {

            "sent_count": sent_count,

            "received_count": received_count,

            "actual_send_rate": actual_send_rate,

            "delivery_ratio": received_count / sent_count if sent_count > 0 else 0

        }

    

    def _assert_rate_performance(self, target_rate: int, metrics: dict):

        """Assert performance requirements for a specific rate."""

        assert metrics["actual_send_rate"] >= target_rate * 0.9, \

            f"Send rate too low at {target_rate} msg/sec: {metrics['actual_send_rate']:.1f}"

        

        assert metrics["delivery_ratio"] >= 0.95, \

            f"Delivery ratio too low at {target_rate} msg/sec: {metrics['delivery_ratio']:.3f}"

    

    def _validate_scaling_linearity(self, scaling_results: dict):

        """Validate linear scaling characteristics."""

        rates = list(scaling_results.keys())

        actual_rates = [scaling_results[r]["actual_send_rate"] for r in rates]

        

        # Test linear scaling up to 5000 msg/sec

        linear_threshold = 5000

        linear_rates = [r for r in rates if r <= linear_threshold]

        linear_actual = [scaling_results[r]["actual_send_rate"] for r in linear_rates]

        

        if len(linear_rates) >= 3:

            correlation = statistics.correlation(linear_rates, linear_actual)

            assert correlation >= 0.95, \

                f"Linear scaling correlation too low: {correlation:.3f}"

        

        # Validate graceful degradation beyond limits

        high_load_rates = [r for r in rates if r > linear_threshold]

        for rate in high_load_rates:

            delivery_ratio = scaling_results[rate]["delivery_ratio"]

            assert delivery_ratio >= 0.8, \

                f"Delivery ratio degraded too much at {rate} msg/sec: {delivery_ratio:.3f}"

    

    def _finalize_test_results(self, test_results: LoadTestResults, scaling_results: dict):

        """Finalize test results with calculated metrics."""

        rates = list(scaling_results.keys())

        actual_rates = [scaling_results[r]["actual_send_rate"] for r in rates]

        

        test_results.end_time = time.time()

        test_results.total_duration = test_results.end_time - test_results.start_time

        test_results.peak_throughput = max(actual_rates)

        

        linear_rates = [r for r in rates if r <= 5000]

        test_results.sustained_throughput = max([

            scaling_results[r]["actual_send_rate"] for r in linear_rates

        ]) if linear_rates else 0

    

    async def _create_multiple_clients(self, count: int) -> list:

        """Create multiple client connections."""

        from tests.e2e.fixtures.high_volume_data import MockAuthenticator

        from tests.e2e.test_helpers.performance_base import (

            HighVolumeThroughputClient,

        )

        

        clients = []

        for i in range(count):

            user = MockAuthenticator.create_test_user()

            client = HighVolumeThroughputClient(

                "ws://localhost:8765", user["token"], f"client-{i}"

            )

            await client.connect()

            clients.append(client)

        

        return clients

    

    async def _run_client_burst(self, client, message_count: int) -> dict:

        """Run message burst for single client."""

        start_time = time.perf_counter()

        results = await client.send_throughput_burst(message_count)

        responses = await client.receive_responses(message_count, timeout=30.0)

        duration = time.perf_counter() - start_time

        

        sent_count = len([r for r in results if r["status"] == "sent"])

        return {

            "sent_count": sent_count,

            "received_count": len(responses),

            "duration": duration

        }

    

    async def _cleanup_clients(self, clients: list):

        """Clean up client connections."""

        for client in clients:

            try:

                await client.disconnect()

            except Exception as e:

                logger.warning(f"Client cleanup error: {e}")

    

    def _validate_connection_scaling(self, scaling_results: dict):

        """Validate connection scaling performance."""

        conn_counts = list(scaling_results.keys())

        throughputs = [scaling_results[c]["throughput"] for c in conn_counts]

        

        # Throughput should not degrade significantly with more connections

        if len(conn_counts) >= 2:

            max_throughput = max(throughputs)

            min_throughput = min(throughputs)

            degradation_ratio = min_throughput / max_throughput

            

            assert degradation_ratio >= 0.7, \

                f"Connection scaling degradation too high: {degradation_ratio:.3f}"

