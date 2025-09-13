"""

Test Suite: Linear Throughput Scaling - E2E Implementation



Business Value Justification (BVJ):

- Segment: Enterprise/Mid

- Business Goal: Platform Scalability Validation

- Value Impact: Ensures system can handle predictable load growth

- Strategic/Revenue Impact: Critical for enterprise scaling contracts



This test validates that the Netra Apex platform scales linearly

with increasing message rates up to system limits.

"""



import asyncio

import logging

import statistics

import time

from typing import Any, Dict

from shared.isolated_environment import IsolatedEnvironment



import pytest



from tests.e2e.test_helpers.throughput_helpers import (

    E2E_TEST_CONFIG,

    LoadTestResults,

    ThroughputMetrics,

    create_test_message,

    measure_system_resources,

)



logger = logging.getLogger(__name__)



# Linear scaling test configuration

LINEAR_SCALING_CONFIG = {

    "message_rate_scaling_steps": [100, 500, 1000, 2500, 5000, 7500, 10000],

    "test_duration_seconds": 30,

    "linear_threshold": 5000,  # Expected linear scaling up to 5000 msg/sec

    "min_correlation": 0.95,   # Minimum linear correlation

    "min_delivery_ratio": 0.95,

    "degraded_delivery_ratio": 0.8  # Acceptable ratio beyond limits

}



class TestLinearThroughputScaling:

    """Test linear throughput scaling characteristics"""

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    @pytest.mark.timeout(300)

    async def test_linear_scaling_validation(self, throughput_client, high_volume_server):

        """Validate system performance scales linearly with increasing message rates"""

        test_results = LoadTestResults(

            test_name="linear_throughput_scaling",

            start_time=time.time(),

            end_time=0,

            total_duration=0

        )

        

        scaling_results = await self._execute_scaling_test(throughput_client)

        self._validate_linear_characteristics(scaling_results)

        self._validate_graceful_degradation(scaling_results)

        

        test_results.end_time = time.time()

        test_results.total_duration = test_results.end_time - test_results.start_time

        

        rates = list(scaling_results.keys())

        actual_rates = [scaling_results[r]["actual_send_rate"] for r in rates]

        test_results.peak_throughput = max(actual_rates)

        

        logger.info(f"Linear scaling test completed: Peak {test_results.peak_throughput:.1f} msg/sec")

    

    async def _execute_scaling_test(self, throughput_client) -> Dict[str, Any]:

        """Execute throughput scaling test across different rates"""

        scaling_results = {}

        

        for rate in LINEAR_SCALING_CONFIG["message_rate_scaling_steps"]:

            logger.info(f"Testing throughput at {rate} msg/sec...")

            

            result = await self._test_single_rate(throughput_client, rate)

            scaling_results[rate] = result

            

            # Performance assertions

            assert result["actual_send_rate"] >= rate * 0.9, \

                f"Send rate too low at {rate}: {result['actual_send_rate']:.1f}"

            

            assert result["delivery_ratio"] >= LINEAR_SCALING_CONFIG["min_delivery_ratio"], \

                f"Delivery ratio too low at {rate}: {result['delivery_ratio']:.3f}"

            

            await asyncio.sleep(2.0)  # Stabilization between tests

        

        return scaling_results

    

    async def _test_single_rate(self, throughput_client, rate: int) -> Dict[str, Any]:

        """Test throughput at a single message rate"""

        duration = LINEAR_SCALING_CONFIG["test_duration_seconds"]

        message_count = rate * duration

        

        start_time = time.perf_counter()

        results = await throughput_client.send_throughput_burst(

            message_count=message_count,

            rate_limit=rate

        )

        send_duration = time.perf_counter() - start_time

        

        responses = await throughput_client.receive_responses(

            expected_count=message_count,

            timeout=60.0

        )

        

        sent_count = len([r for r in results if r["status"] == "sent"])

        received_count = len(responses)

        actual_send_rate = sent_count / send_duration if send_duration > 0 else 0

        delivery_ratio = received_count / sent_count if sent_count > 0 else 0

        

        return {

            "target_rate": rate,

            "actual_send_rate": actual_send_rate,

            "delivery_ratio": delivery_ratio,

            "sent_count": sent_count,

            "received_count": received_count,

            "send_duration": send_duration

        }

    

    def _validate_linear_characteristics(self, scaling_results: Dict[str, Any]):

        """Validate linear scaling characteristics"""

        linear_threshold = LINEAR_SCALING_CONFIG["linear_threshold"]

        rates = list(scaling_results.keys())

        

        linear_rates = [r for r in rates if r <= linear_threshold]

        linear_actual = [scaling_results[r]["actual_send_rate"] for r in linear_rates]

        

        if len(linear_rates) >= 3:

            correlation = statistics.correlation(linear_rates, linear_actual)

            assert correlation >= LINEAR_SCALING_CONFIG["min_correlation"], \

                f"Linear scaling correlation too low: {correlation:.3f}"

            

            logger.info(f"Linear scaling correlation: {correlation:.3f}")

    

    def _validate_graceful_degradation(self, scaling_results: Dict[str, Any]):

        """Validate graceful degradation beyond linear scaling limits"""

        linear_threshold = LINEAR_SCALING_CONFIG["linear_threshold"]

        degraded_ratio = LINEAR_SCALING_CONFIG["degraded_delivery_ratio"]

        

        high_load_rates = [r for r in scaling_results.keys() if r > linear_threshold]

        

        for rate in high_load_rates:

            delivery_ratio = scaling_results[rate]["delivery_ratio"]

            assert delivery_ratio >= degraded_ratio, \

                f"Delivery ratio degraded too much at {rate}: {delivery_ratio:.3f}"

    

    @pytest.mark.asyncio

    async def test_sustained_linear_performance(self, throughput_client, high_volume_server):

        """Test sustained performance at optimal linear scaling rate"""

        optimal_rate = 2500  # Mid-range linear scaling rate

        sustained_duration = 120  # 2 minutes

        

        logger.info(f"Testing sustained performance at {optimal_rate} msg/sec for {sustained_duration}s")

        

        start_time = time.time()

        total_sent = 0

        total_received = 0

        

        # Run test in 30-second intervals

        interval_duration = 30

        intervals = sustained_duration // interval_duration

        

        for interval in range(intervals):

            interval_start = time.perf_counter()

            message_count = optimal_rate * interval_duration

            

            results = await throughput_client.send_throughput_burst(

                message_count=message_count,

                rate_limit=optimal_rate

            )

            

            responses = await throughput_client.receive_responses(

                expected_count=message_count,

                timeout=60.0

            )

            

            interval_sent = len([r for r in results if r["status"] == "sent"])

            interval_received = len(responses)

            

            total_sent += interval_sent

            total_received += interval_received

            

            # Validate performance maintains linear characteristics

            interval_duration_actual = time.perf_counter() - interval_start

            actual_rate = interval_sent / interval_duration_actual

            

            assert actual_rate >= optimal_rate * 0.9, \

                f"Sustained rate dropped in interval {interval}: {actual_rate:.1f}"

            

            delivery_ratio = interval_received / interval_sent if interval_sent > 0 else 0

            assert delivery_ratio >= 0.95, \

                f"Delivery ratio dropped in interval {interval}: {delivery_ratio:.3f}"

            

            logger.info(f"Interval {interval}: {actual_rate:.1f} msg/sec, "

                       f"delivery: {delivery_ratio:.3f}")

        

        total_duration = time.time() - start_time

        overall_rate = total_sent / total_duration

        overall_delivery = total_received / total_sent if total_sent > 0 else 0

        

        logger.info(f"Sustained test completed: {overall_rate:.1f} msg/sec average, "

                   f"{overall_delivery:.3f} delivery ratio")

        

        # Final assertions

        assert overall_rate >= optimal_rate * 0.9, \

            f"Overall sustained rate too low: {overall_rate:.1f}"

        assert overall_delivery >= 0.95, \

            f"Overall delivery ratio too low: {overall_delivery:.3f}"

