"""
Test LLM Integration

Validates LLM API integrations (Gemini, OpenAI, Anthropic)
with staging API keys.
"""""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from shared.isolated_environment import IsolatedEnvironment


import pytest
# Test framework import - using pytest fixtures instead

import asyncio
import os
from typing import Dict, Optional

import httpx

from netra_backend.tests.integration.staging_config.base import StagingConfigTestBase

class TestLLMIntegration(StagingConfigTestBase):
    """Test LLM integrations in staging."""

    @pytest.mark.asyncio
    async def test_gemini_api_connection(self):
        """Test Gemini API connectivity with staging key."""
        self.skip_if_not_staging()
        self.require_gcp_credentials()

        try:
            api_key = self.assert_secret_exists('gemini-api-key')
        except AssertionError:
            self.skipTest("Gemini API key not configured")

        # Test Gemini API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}",
                json={
                "contents": [{
                "parts": [{
                "text": "Hello, this is a test. Reply with 'OK'"
                }]
                }]
                },
                timeout=30.0
                )

                self.assertEqual(response.status_code, 200,
                f"Gemini API failed: {response.status_code}")

                data = response.json()
                self.assertIn('candidates', data,
                "Gemini response missing candidates")

                @pytest.mark.asyncio
                async def test_openai_api_connection(self):
                    """Test OpenAI API connectivity with staging key."""
                    self.skip_if_not_staging()
                    self.require_gcp_credentials()

                    try:
                        api_key = self.assert_secret_exists('openai-api-key')
                    except AssertionError:
                        self.skipTest("OpenAI API key not configured")

        # Test OpenAI API
                        async with httpx.AsyncClient() as client:
                            response = await client.post(
                            "https://api.openai.com/chat/completions",
                            headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                            },
                            json={
                            "model": LLMModel.GEMINI_2_5_FLASH.value,
                            "messages": [
                            {"role": "user", "content": "Reply with 'OK'"}
                            ],
                            "max_tokens": 10
                            },
                            timeout=30.0
                            )

                            self.assertEqual(response.status_code, 200,
                            f"OpenAI API failed: {response.status_code}")

                            data = response.json()
                            self.assertIn('choices', data,
                            "OpenAI response missing choices")

                            @pytest.mark.asyncio
                            async def test_anthropic_api_connection(self):
                                """Test Anthropic API connectivity with staging key."""
                                self.skip_if_not_staging()
                                self.require_gcp_credentials()

                                try:
                                    api_key = self.assert_secret_exists('anthropic-api-key')
                                except AssertionError:
                                    self.skipTest("Anthropic API key not configured")

        # Test Anthropic API
                                    async with httpx.AsyncClient() as client:
                                        response = await client.post(
                                        "https://api.anthropic.com/messages",
                                        headers={
                                        "x-api-key": api_key,
                                        "anthropic-version": "2023-06-01",
                                        "Content-Type": "application/json"
                                        },
                                        json={
                                        "model": "claude-3-haiku-20240307",
                                        "messages": [
                                        {"role": "user", "content": "Reply with 'OK'"}
                                        ],
                                        "max_tokens": 10
                                        },
                                        timeout=30.0
                                        )

                                        self.assertEqual(response.status_code, 200,
                                        f"Anthropic API failed: {response.status_code}")

                                        data = response.json()
                                        self.assertIn('content', data,
                                        "Anthropic response missing content")

                                        @pytest.mark.asyncio
                                        async def test_llm_rate_limiting(self):
                                            """Test LLM API rate limiting handling."""
                                            self.skip_if_not_staging()

        # Test rate limit handling through application
                                            async with httpx.AsyncClient() as client:
            # Make rapid requests to trigger rate limiting
                                                responses = []

                                                for i in range(5):
                                                    response = await client.post(
                                                    f"{self.staging_url}/api/chat/completions",
                                                    json={
                                                    "model": "gemini-pro",
                                                    "messages": [
                                                    {"role": "user", "content": f"Test {i}"}
                                                    ]
                                                    },
                                                    headers={
                                                    "Authorization": f"Bearer test_token"
                                                    },
                                                    timeout=10.0
                                                    )
                                                    responses.append(response.status_code)

            # Should handle rate limits gracefully
                                                    for status in responses:
                                                        self.assertIn(status, [200, 429, 503],
                                                        f"Unexpected status: {status}")

                                                        @pytest.mark.asyncio
                                                        async def test_llm_fallback(self):
                                                            """Test LLM provider fallback mechanism."""
                                                            self.skip_if_not_staging()

        # Test fallback when primary provider fails
                                                            async with httpx.AsyncClient() as client:
                                                                response = await client.post(
                                                                f"{self.staging_url}/api/chat/completions",
                                                                json={
                                                                "model": "auto",  # Should use fallback logic
                                                                "messages": [
                                                                {"role": "user", "content": "Test fallback"}
                                                                ],
                                                                "providers": ["gemini", "openai", "anthropic"]
                                                                },
                                                                headers={
                                                                "Authorization": f"Bearer test_token"
                                                                },
                                                                timeout=30.0
                                                                )

                                                                if response.status_code == 200:
                                                                    data = response.json()
                                                                    self.assertIn('provider_used', data,
                                                                    "Response should indicate which provider was used")

                                                                    @pytest.mark.asyncio
                                                                    async def test_llm_timeout_handling(self):
                                                                        """Test LLM timeout handling."""
                                                                        self.skip_if_not_staging()

                                                                        async with httpx.AsyncClient() as client:
            # Test with very short timeout
                                                                            response = await client.post(
                                                                            f"{self.staging_url}/api/chat/completions",
                                                                            json={
                                                                            "model": "gemini-pro",
                                                                            "messages": [
                                                                            {"role": "user", "content": "Generate a very long response"}
                                                                            ],
                                                                            "timeout_ms": 100  # Very short timeout
                                                                            },
                                                                            headers={
                                                                            "Authorization": f"Bearer test_token"
                                                                            },
                                                                            timeout=5.0
                                                                            )

            # Should handle timeout gracefully
                                                                            self.assertIn(response.status_code, [408, 504],
                                                                            "Should return timeout status")

                                                                            @pytest.mark.asyncio
                                                                            async def test_llm_context_limits(self):
                                                                                """Test LLM context limit handling."""
                                                                                self.skip_if_not_staging()

        # Create very long message to test context limits
                                                                                long_message = "Test " * 10000  # ~50k characters

                                                                                async with httpx.AsyncClient() as client:
                                                                                    response = await client.post(
                                                                                    f"{self.staging_url}/api/chat/completions",
                                                                                    json={
                                                                                    "model": "gemini-pro",
                                                                                    "messages": [
                                                                                    {"role": "user", "content": long_message}
                                                                                    ]
                                                                                    },
                                                                                    headers={
                                                                                    "Authorization": f"Bearer test_token"
                                                                                    },
                                                                                    timeout=30.0
                                                                                    )

            # Should handle context limits
                                                                                    if response.status_code == 400:
                                                                                        data = response.json()
                                                                                        self.assertIn('context', data.get('error', '').lower(),
                                                                                        "Should indicate context limit error")