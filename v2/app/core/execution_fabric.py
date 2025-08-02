# netra_apex/core/execution_fabric.py
#
# Copyright (C) 2025, netra apex Inc.
#
# This module implements the Execution Fabric, the "hands" of the system. It is
# responsible for taking a concrete routing decision from the controller and
# safely enacting it. It interfaces with the actual model endpoints (mocked in
# this simulation), executes the workload, and captures critical performance
# metrics during the process. The results are then passed to the Observability
# Plane to close the feedback loop.
# Reference: Section 6: The Execution Fabric and Governance Layer.

import time
import random
from typing import Dict, Any

from ..models.schemas import WorkloadProfile, SupplyRecord
from .observability import ObservabilityPlane

class MockModelEndpoint:
    """
    A mock class that simulates a real model inference endpoint. It generates
    a plausible-sounding response and simulates latency characteristics based
    on the model's known profile.
    """
    def __init__(self, supply_record: SupplyRecord):
        self.supply_record = supply_record
        # Use model name for deterministic randomness
        seed = int.from_bytes(supply_record.model_name.encode(), 'little') % (2**32 - 1)
        self.random_generator = random.Random(seed)

    def generate_response(self, prompt: str) -> Dict[str, Any]:
        """
        Simulates the entire inference process, including latency and text output.
        """
        start_time = time.time()

        # Simulate TTFT (Time To First Token)
        # Base latency from profile, with some random variance
        base_ttft = self.supply_record.performance.ttft_ms.get("batch_1").p50
        simulated_ttft_ms = self.random_generator.gauss(base_ttft, base_ttft * 0.15)
        time.sleep(simulated_ttft_ms / 1000.0)
        first_token_time = time.time()

        # Generate a mock text response
        output_text = f"Response from {self.supply_record.model_name}: The query was '{prompt[:30]}...'. Acknowledged."
        if self.supply_record.model_name == "experimental-model-v0.1":
             output_text += " This is an experimental, possibly buggy, response."
        if "treatment" in prompt:
             output_text += " As an AI, I cannot provide medical advice. Please consult a doctor."


        # Simulate TPOT (Time Per Output Token)
        output_token_count = len(output_text.split())
        base_tpot = self.supply_record.performance.tpot_ms.get("batch_1").p50
        for _ in range(output_token_count):
            simulated_tpot_ms = self.random_generator.gauss(base_tpot, base_tpot * 0.1)
            time.sleep(simulated_tpot_ms / 1000.0)

        end_time = time.time()

        return {
            "output_text": output_text,
            "metrics": {
                "ttft_ms": (first_token_time - start_time) * 1000,
                "tpot_ms": ((end_time - first_token_time) * 1000) / output_token_count if output_token_count > 0 else 0,
                "total_time_ms": (end_time - start_time) * 1000
            }
        }

class ExecutionFabric:
    """
    Orchestrates the execution of a workload on a chosen supply option.
    """
    def __init__(self, observability_plane: ObservabilityPlane):
        """
        Initializes the Execution Fabric.

        Args:
            observability_plane: An instance of the ObservabilityPlane to send results to.
        """
        self.observability_plane = observability_plane
        # A cache of mock endpoints to avoid re-initializing them
        self._endpoint_cache: Dict[str, MockModelEndpoint] = {}
        print("ExecutionFabric initialized.")

    def _get_endpoint(self, supply_record: SupplyRecord) -> MockModelEndpoint:
        """
        Retrieves or creates a mock endpoint for the given supply record.
        """
        if supply_record.supply_id not in self._endpoint_cache:
            print(f"ExecutionFabric: Spinning up new mock endpoint for {supply_record.model_name}")
            self._endpoint_cache[supply_record.supply_id] = MockModelEndpoint(supply_record)
        return self._endpoint_cache[supply_record.supply_id]

    def execute_workload(self, workload: WorkloadProfile, supply_record: SupplyRecord) -> Dict[str, Any]:
        """
        Executes the workload, captures the results, and forwards them to the
        Observability Plane for analysis.

        Args:
            workload: The WorkloadProfile to be executed.
            supply_record: The SupplyRecord of the chosen model.

        Returns:
            The raw execution result, including the model's output and metrics.
        """
        if not supply_record.performance:
             raise ValueError(f"Cannot execute on {supply_record.model_name} as it has no performance profile.")
             
        print(f"\n---> Executing workload {workload.workload_id[:8]} on supply {supply_record.model_name} <---")
        
        endpoint = self._get_endpoint(supply_record)
        execution_result = endpoint.generate_response(workload.raw_prompt)

        print(f"Execution Result: TTFT={execution_result['metrics']['ttft_ms']:.2f}ms, Output='{execution_result['output_text'][:50]}...'")

        # Asynchronously send the result to the observability plane to close the loop
        # (Here, we call it directly for simplicity)
        self.observability_plane.process_completed_workload(
            workload=workload,
            supply_id=supply_record.supply_id,
            execution_result=execution_result
        )

        return execution_result
