"""Test-compatible DataSubAgent that includes all backward compatibility methods."""

from app.agents.data_sub_agent.agent import DataSubAgent as BaseDataSubAgent
from app.tests.helpers.data_sub_agent_test_compatibility import TestCompatibilityMixin


class DataSubAgent(BaseDataSubAgent, TestCompatibilityMixin):
    """DataSubAgent with test compatibility methods included."""
    pass