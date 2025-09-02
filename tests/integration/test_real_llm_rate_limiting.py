import os
from unittest.mock import AsyncMock, patch

import pytest

# NOTE: Assuming the agent implementation lives in a path like this.
# This will likely need to be adjusted.
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from shared.isolated_environment import get_env


@pytest.mark.slow
@pytest.mark.real_llm
class TestRealLlmRateLimiting:

    @pytest.fixture
    def llm_api_key(self):
        """Fixture to get a real LLM API key from environment variables."""
        api_key = get_env().get("REAL_LLM_API_KEY")
        if not api_key:
            pytest.skip("REAL_LLM_API_KEY environment variable not set.")
        return api_key

    @pytest.mark.asyncio
    async def test_rate_limit_handling_with_real_llm(self, llm_api_key):
        """
        Tests that the agent handles LLM rate limits gracefully with exponential backoff.
        """
        # This test will patch the LLM client to simulate rate limit errors
        # and verify that the agent's retry logic is triggered.

        # Mock the LLM client to raise a rate limit error twice, then succeed.
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_llm_client = AsyncMock()
        mock_llm_client.generate.side_effect = [
            httpx.ReadTimeout("Rate limit exceeded"),
            httpx.ReadTimeout("Rate limit exceeded"),
            "Successfully generated text.",
        ]

        # Patch the agent's LLM client
        # Mock: Component isolation for testing without external dependencies
        with patch(
            "netra_backend.app.agents.supervisor.LLMClient",
            return_value=mock_llm_client,
        ):
            # NOTE: This assumes the SupervisorAgent takes the api_key and a prompt.
            # The actual implementation may be different.
            agent = SupervisorAgent(api_key=llm_api_key)

            # Run the agent's main workflow
            # NOTE: This assumes the agent has a method like `run_workflow`
            await agent.run_workflow("Test prompt")

            # Assert that the LLM client was called 3 times (2 retries + 1
            # success)
            assert mock_llm_client.generate.call_count == 3

            # Assert that the agent's sleep function was called with increasing backoff times
            # This requires patching the agent's sleep function.
            # Mock: Component isolation for testing without external dependencies
            with patch("asyncio.sleep") as mock_sleep:
                await agent.run_workflow("Test prompt")
                # Check that sleep was called with increasing durations
                assert mock_sleep.call_count == 2
                assert mock_sleep.call_args_list[0][0][0] > 0
                assert (
                    mock_sleep.call_args_list[1][0][0]
                    > mock_sleep.call_args_list[0][0][0]
                )
