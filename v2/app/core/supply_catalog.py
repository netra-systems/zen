# netra_apex/core/supply_catalog.py
#
# Copyright (C) 2025, netra apex Inc.
#
# This module implements the Supply Catalog, the single source of truth for all
# available AI models and compute resources. It acts as a dynamic, in-memory
# database that is continuously updated by the Observability & Feedback Plane.
# Its primary role is to provide the Multi-Objective Controller with a rich,
# consistent, and up-to-date view of the entire supply portfolio, enabling
# data-driven, multi-faceted comparisons between heterogeneous options.
# Reference: Section 3: The Supply Catalog.

import uuid
from typing import Dict, List, Optional
from threading import Lock

# Assuming schemas are in a sibling directory `models`
from ..models.schemas import SupplyRecord, LatencyDistributions, SafetyAndQualityProfile

class SupplyCatalog:
    """
    A dynamic and comprehensive registry of all available AI supply options.
    This class provides thread-safe CRUD operations for managing SupplyRecords
    and serves as the central repository for model capabilities, costs, and
    real-time performance data.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        """
        Singleton pattern to ensure only one instance of the Supply Catalog
        exists in the system, preventing data fragmentation.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the SupplyCatalog with an in-memory dictionary to store
        supply records. In a production system, this could be backed by a
        persistent database like Redis or a dedicated time-series database.
        """
        # The check `hasattr(self, '_initialized')` prevents re-initialization
        # in the singleton pattern.
        if not hasattr(self, '_initialized'):
            self._catalog: Dict[uuid.UUID, SupplyRecord] = {}
            self._lock = Lock()  # Instance-level lock for thread-safe operations
            self._initialized = True
            print("SupplyCatalog initialized.")

    def add_supply_record(self, record: SupplyRecord) -> uuid.UUID:
        """
        Adds a new supply record to the catalog. This is typically done during
        system startup or when a new model is onboarded. A new UUID is generated
        if one is not provided.

        Args:
            record: A SupplyRecord object to be added.

        Returns:
            The UUID of the added record.
        """
        if not isinstance(record, SupplyRecord):
            raise TypeError("record must be an instance of SupplyRecord")

        with self._lock:
            if record.supply_id in self._catalog:
                raise ValueError(f"Supply record with ID {record.supply_id} already exists.")
            self._catalog[record.supply_id] = record
            print(f"Added supply record: {record.model_name} ({record.supply_id})")
            return record.supply_id

    def get_supply_record(self, supply_id: uuid.UUID) -> Optional[SupplyRecord]:
        """
        Retrieves a specific supply record by its unique identifier.

        Args:
            supply_id: The UUID of the supply record to retrieve.

        Returns:
            The SupplyRecord object if found, otherwise None.
        """
        with self._lock:
            return self._catalog.get(supply_id)

    def list_all_records(self) -> List[SupplyRecord]:
        """
        Returns a list of all supply records currently in the catalog.

        Returns:
            A list of all SupplyRecord objects.
        """
        with self._lock:
            return list(self._catalog.values())

    def list_certified_records(self) -> List[SupplyRecord]:
        """
        Returns a list of all supply records that have been certified by the
        Adversarial Gauntlet, making them eligible for production workloads.
        Reference: Section 5, Component 3: The Adversarial Gauntlet.

        Returns:
            A list of gauntlet-certified SupplyRecord objects.
        """
        with self._lock:
            return [
                record for record in self._catalog.values()
                if record.is_gauntlet_certified
            ]

    def remove_supply_record(self, supply_id: uuid.UUID) -> bool:
        """
        Removes a supply record from the catalog, for example, when a model is
        decommissioned.

        Args:
            supply_id: The UUID of the record to remove.

        Returns:
            True if the record was successfully removed, False if it was not found.
        """
        with self._lock:
            if supply_id in self._catalog:
                del self._catalog[supply_id]
                print(f"Removed supply record: {supply_id}")
                return True
            return False

    def update_performance_data(
        self,
        supply_id: uuid.UUID,
        performance_data: LatencyDistributions
    ) -> bool:
        """
        Updates the real-time performance distributions for a specific supply
        option. This method is called by the Observability & Feedback Plane.
        Reference: Section 3, Component 2 & Section 5.

        Args:
            supply_id: The UUID of the supply record to update.
            performance_data: A LatencyDistributions object with the latest metrics.

        Returns:
            True if the update was successful, False if the record was not found.
        """
        with self._lock:
            record = self._catalog.get(supply_id)
            if record:
                record.performance = performance_data
                # In a real system, you might want to log this update or emit an event.
                # print(f"Updated performance for {record.model_name}")
                return True
            return False

    def update_safety_and_quality_data(
        self,
        supply_id: uuid.UUID,
        quality_data: SafetyAndQualityProfile
    ) -> bool:
        """
        Updates the real-time safety and quality profile for a supply option.
        This is a critical part of the closed-loop mechanism, called by the
        Observability & Feedback Plane.
        Reference: Section 3, Component 2 & Section 5.

        Args:
            supply_id: The UUID of the supply record to update.
            quality_data: A SafetyAndQualityProfile object with the latest scores.

        Returns:
            True if the update was successful, False if the record was not found.
        """
        with self._lock:
            record = self._catalog.get(supply_id)
            if record:
                record.safety_and_quality = quality_data
                # print(f"Updated safety/quality profile for {record.model_name}")
                return True
            return False

    def certify_model(self, supply_id: uuid.UUID) -> bool:
        """
        Marks a model as having passed the Adversarial Gauntlet. This is
        typically called by the governance workflow after a successful evaluation.
        Reference: Section 5, Component 3: The Adversarial Gauntlet.

        Args:
            supply_id: The UUID of the model to certify.

        Returns:
            True if certification was successful, False if the record was not found.
        """
        with self._lock:
            record = self._catalog.get(supply_id)
            if record:
                if not record.is_gauntlet_certified:
                    record.is_gauntlet_certified = True
                    print(f"Certified model: {record.model_name}")
                return True
            return False

    def get_record_by_name(self, model_name: str) -> Optional[SupplyRecord]:
        """
        Utility method to find a supply record by its model name. Assumes names are unique.

        Args:
            model_name: The name of the model to find.

        Returns:
            The SupplyRecord object if found, otherwise None.
        """
        with self._lock:
            for record in self._catalog.values():
                if record.model_name == model_name:
                    return record
            return None

# Example usage (can be placed in a main script or test file)
def populate_initial_catalog(catalog: SupplyCatalog):
    """A helper function to populate the catalog with sample data for demonstration."""
    from ..models.schemas import CostModel, TechnicalSpecs, TokenizerProfile, TokenizerAlgorithm, DeploymentType
    import uuid

    # Based on Table 4 and other contextual data from the document
    sample_records = [
        SupplyRecord(
            supply_id=uuid.uuid4(),
            model_name="claude-3-haiku-20240307",
            provider="Anthropic",
            deployment_type=DeploymentType.API,
            cost_model=CostModel(type="API", input_cost_per_million_tokens=0.25, output_cost_per_million_tokens=1.25),
            technical_specs=TechnicalSpecs(max_context_window=200000, modalities=["text", "image"], quantization=None, architecture="Transformer"),
            tokenizer_profile=TokenizerProfile(library="anthropic", name="claude-v1", algorithm=TokenizerAlgorithm.BPE, vocab_size=100256),
            is_gauntlet_certified=True,
        ),
        SupplyRecord(
            supply_id=uuid.uuid4(),
            model_name="meta-llama/Llama-3-8B-Instruct",
            provider="Self-Hosted",
            deployment_type=DeploymentType.SELF_HOSTED_ONPREM,
            cost_model=CostModel(type="TCO", tco_model_id="tier1_a100_v2", amortized_cost_per_hour=2.50),
            technical_specs=TechnicalSpecs(max_context_window=8192, modalities=["text"], quantization="AWQ-4bit", hardware_requirements={"min_vram_gb": 16}),
            tokenizer_profile=TokenizerProfile(library="tiktoken", name="cl100k_base", algorithm=TokenizerAlgorithm.BPE, vocab_size=100256),
            is_gauntlet_certified=True,
        ),
        SupplyRecord(
            supply_id=uuid.uuid4(),
            model_name="google/gemini-1.5-pro-latest",
            provider="Google",
            deployment_type=DeploymentType.API,
            cost_model=CostModel(type="API", input_cost_per_million_tokens=3.50, output_cost_per_million_tokens=10.50),
            technical_specs=TechnicalSpecs(max_context_window=1000000, modalities=["text", "image", "video", "audio"], architecture="Mixture-of-Experts"),
            tokenizer_profile=TokenizerProfile(library="sentencepiece", name="gemini-1.5", algorithm=TokenizerAlgorithm.SENTENCEPIECE, vocab_size=256000),
            is_gauntlet_certified=True,
        ),
         SupplyRecord(
            supply_id=uuid.uuid4(),
            model_name="experimental-model-v0.1",
            provider="Internal R&D",
            deployment_type=DeploymentType.SELF_HOSTED_CLOUD,
            cost_model=CostModel(type="TCO", tco_model_id="dev_cluster_spot", amortized_cost_per_hour=0.75),
            technical_specs=TechnicalSpecs(max_context_window=4096, modalities=["text"], quantization="FP16"),
            tokenizer_profile=TokenizerProfile(library="huggingface", name="bert-base-uncased", algorithm=TokenizerAlgorithm.WORDPIECE, vocab_size=30522),
            is_gauntlet_certified=False, # Not yet certified
        )
    ]

    for rec in sample_records:
        catalog.add_supply_record(rec)
