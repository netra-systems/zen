#!/usr/bin/env python3
"""
Claude Code Pricing Compliance Engine

Provides accurate token counting and cost calculation based on official Claude pricing.
Designed to be the SSOT for all Claude Code pricing calculations within zen.

Key Features:
- Model detection from API responses
- Accurate cache pricing based on duration
- Tool cost calculation
- Compliance with Claude pricing documentation
- Extensible for future Claude Code agent support
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any
import re
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class ClaudePricingConfig:
    """Current Claude pricing rates as of 2024-2025"""

    # Model pricing per million tokens (input, output)
    MODEL_PRICING = {
        "claude-opus-4": {"input": 15.0, "output": 75.0},
        "claude-opus-4.1": {"input": 15.0, "output": 75.0},
        "claude-sonnet-4": {"input": 3.0, "output": 15.0},
        "claude-sonnet-3.7": {"input": 3.0, "output": 15.0},
        "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
        "claude-haiku-3.5": {"input": 0.8, "output": 4.0},
    }

    # Cache pricing multipliers
    CACHE_READ_MULTIPLIER = 0.1  # 10% of base input price
    CACHE_5MIN_WRITE_MULTIPLIER = 1.25  # 25% premium
    CACHE_1HOUR_WRITE_MULTIPLIER = 2.0  # 100% premium

    # Tool pricing (per 1000 calls)
    TOOL_PRICING = {
        "web_search": 10.0,  # $10 per 1000 searches
        "web_fetch": 0.0,    # No additional charge
        "default": 0.0       # Most tools have no additional charge
    }

@dataclass
class TokenUsageData:
    """Token usage data with detailed breakdown"""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_type: str = "5min"  # "5min" or "1hour"
    total_tokens: int = 0
    tool_calls: int = 0
    model: str = "claude-3-5-sonnet"

    def __post_init__(self):
        """Calculate total if not provided"""
        if self.total_tokens == 0:
            self.total_tokens = (self.input_tokens + self.output_tokens +
                               self.cache_read_tokens + self.cache_creation_tokens)

@dataclass
class CostBreakdown:
    """Detailed cost breakdown for transparency"""
    input_cost: float = 0.0
    output_cost: float = 0.0
    cache_read_cost: float = 0.0
    cache_creation_cost: float = 0.0
    tool_cost: float = 0.0
    total_cost: float = 0.0
    model_used: str = ""
    cache_type: str = ""

    def __post_init__(self):
        """Calculate total cost"""
        self.total_cost = (self.input_cost + self.output_cost +
                          self.cache_read_cost + self.cache_creation_cost + self.tool_cost)

class ClaudePricingEngine:
    """
    Claude Code pricing compliance engine for accurate cost calculation.

    Ensures compliance with official Claude pricing documentation and provides
    detailed transparency for token usage costs.
    """

    def __init__(self):
        self.pricing_config = ClaudePricingConfig()

    def detect_model_from_response(self, response_data: Dict[str, Any]) -> str:
        """
        Detect Claude model from API response or usage data.

        Args:
            response_data: API response or usage data containing model information

        Returns:
            Model name string, defaults to claude-3-5-sonnet if not detected
        """
        # Try multiple locations where model might be specified
        model_locations = [
            response_data.get('model'),
            response_data.get('model_name'),
            response_data.get('usage', {}).get('model'),
            response_data.get('message', {}).get('model'),
            response_data.get('metadata', {}).get('model')
        ]

        for model in model_locations:
            if model and isinstance(model, str):
                # Normalize model name
                normalized = self._normalize_model_name(model)
                if normalized in self.pricing_config.MODEL_PRICING:
                    return normalized

        # Default fallback
        logger.debug("Model not detected in response, defaulting to claude-3-5-sonnet")
        return "claude-3-5-sonnet"

    def _normalize_model_name(self, model_name: str) -> str:
        """Normalize model name to match pricing config keys"""
        model_name = model_name.lower().strip()

        # Handle various model name formats
        if "opus" in model_name:
            if "4.1" in model_name:
                return "claude-opus-4.1"
            elif "4" in model_name:
                return "claude-opus-4"
        elif "sonnet" in model_name:
            if "4" in model_name:
                return "claude-sonnet-4"
            elif "3.7" in model_name:
                return "claude-sonnet-3.7"
            elif "3.5" in model_name or "3-5" in model_name:
                return "claude-3-5-sonnet"
        elif "haiku" in model_name:
            if "3.5" in model_name:
                return "claude-haiku-3.5"

        return model_name

    def detect_cache_type(self, response_data: Dict[str, Any]) -> str:
        """
        Detect cache type (5min vs 1hour) from response data.

        Args:
            response_data: API response data

        Returns:
            "5min" or "1hour", defaults to "5min"
        """
        # Look for cache type indicators in response
        cache_indicators = [
            response_data.get('cache_type'),
            response_data.get('usage', {}).get('cache_type'),
            response_data.get('metadata', {}).get('cache_type')
        ]

        for indicator in cache_indicators:
            if indicator:
                if "1hour" in str(indicator).lower() or "60min" in str(indicator).lower():
                    return "1hour"
                elif "5min" in str(indicator).lower():
                    return "5min"

        # Default to 5min cache
        return "5min"

    def calculate_cost(self, usage_data: TokenUsageData,
                      authoritative_cost: Optional[float] = None,
                      tool_tokens: Optional[Dict[str, int]] = None) -> CostBreakdown:
        """
        Calculate detailed cost breakdown with Claude pricing compliance.

        Args:
            usage_data: Token usage information
            authoritative_cost: SDK-provided cost (preferred when available)
            tool_tokens: Dictionary of tool names to token counts for tool cost calculation

        Returns:
            Detailed cost breakdown for transparency
        """
        # Use authoritative cost if provided (most accurate)
        if authoritative_cost is not None:
            breakdown = CostBreakdown(
                model_used=usage_data.model,
                cache_type=usage_data.cache_type
            )
            breakdown.total_cost = authoritative_cost
            return breakdown

        # Get model pricing
        model_pricing = self.pricing_config.MODEL_PRICING.get(
            usage_data.model,
            self.pricing_config.MODEL_PRICING["claude-3-5-sonnet"]
        )

        # Calculate base costs
        input_cost = (usage_data.input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (usage_data.output_tokens / 1_000_000) * model_pricing["output"]

        # Calculate cache costs with correct multipliers
        cache_read_cost = (usage_data.cache_read_tokens / 1_000_000) * \
                         (model_pricing["input"] * self.pricing_config.CACHE_READ_MULTIPLIER)

        # Cache creation cost depends on cache type
        cache_multiplier = (self.pricing_config.CACHE_1HOUR_WRITE_MULTIPLIER
                           if usage_data.cache_type == "1hour"
                           else self.pricing_config.CACHE_5MIN_WRITE_MULTIPLIER)

        cache_creation_cost = (usage_data.cache_creation_tokens / 1_000_000) * \
                             (model_pricing["input"] * cache_multiplier)

        # Calculate tool costs based on token usage
        tool_cost = 0.0
        if tool_tokens:
            for tool_name, tokens in tool_tokens.items():
                # Tool tokens are charged at the same rate as input tokens for the model
                tool_cost += (tokens / 1_000_000) * model_pricing["input"]

        return CostBreakdown(
            input_cost=input_cost,
            output_cost=output_cost,
            cache_read_cost=cache_read_cost,
            cache_creation_cost=cache_creation_cost,
            tool_cost=tool_cost,
            model_used=usage_data.model,
            cache_type=usage_data.cache_type
        )

    def parse_claude_response(self, response_line: str) -> Optional[TokenUsageData]:
        """
        Parse token usage from Claude Code response line with model detection.

        Args:
            response_line: Single line from Claude Code output

        Returns:
            TokenUsageData if parsing successful, None otherwise
        """
        line = response_line.strip()
        if not line.startswith('{'):
            return None

        try:
            json_data = json.loads(line)

            # Detect model and cache type
            model = self.detect_model_from_response(json_data)
            cache_type = self.detect_cache_type(json_data)

            # Extract usage data
            usage_data = None
            if 'usage' in json_data:
                usage_data = json_data['usage']
            elif 'message' in json_data and isinstance(json_data['message'], dict):
                usage_data = json_data['message'].get('usage')

            if usage_data and isinstance(usage_data, dict):
                return TokenUsageData(
                    input_tokens=int(usage_data.get('input_tokens', 0)),
                    output_tokens=int(usage_data.get('output_tokens', 0)),
                    cache_read_tokens=int(usage_data.get('cache_read_input_tokens', 0)),
                    cache_creation_tokens=int(usage_data.get('cache_creation_input_tokens', 0)),
                    total_tokens=int(usage_data.get('total_tokens', 0)),
                    model=model,
                    cache_type=cache_type
                )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.debug(f"Failed to parse Claude response: {e}")

        return None

    def get_transparency_report(self, usage_data: TokenUsageData,
                               cost_breakdown: CostBreakdown,
                               tool_tokens: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        Generate transparency report for token usage and costs.

        Args:
            usage_data: Token usage information
            cost_breakdown: Detailed cost breakdown
            tool_tokens: Tool-specific token usage

        Returns:
            Comprehensive transparency report
        """
        return {
            "model_used": usage_data.model,
            "cache_type": usage_data.cache_type,
            "token_breakdown": {
                "input_tokens": usage_data.input_tokens,
                "output_tokens": usage_data.output_tokens,
                "cache_read_tokens": usage_data.cache_read_tokens,
                "cache_creation_tokens": usage_data.cache_creation_tokens,
                "total_tokens": usage_data.total_tokens,
                "tool_tokens": tool_tokens or {}
            },
            "cost_breakdown": {
                "input_cost_usd": round(cost_breakdown.input_cost, 6),
                "output_cost_usd": round(cost_breakdown.output_cost, 6),
                "cache_read_cost_usd": round(cost_breakdown.cache_read_cost, 6),
                "cache_creation_cost_usd": round(cost_breakdown.cache_creation_cost, 6),
                "tool_cost_usd": round(cost_breakdown.tool_cost, 6),
                "total_cost_usd": round(cost_breakdown.total_cost, 6)
            },
            "pricing_rates": {
                "model_rates": self.pricing_config.MODEL_PRICING[usage_data.model],
                "cache_read_multiplier": self.pricing_config.CACHE_READ_MULTIPLIER,
                "cache_write_multiplier": (self.pricing_config.CACHE_1HOUR_WRITE_MULTIPLIER
                                         if usage_data.cache_type == "1hour"
                                         else self.pricing_config.CACHE_5MIN_WRITE_MULTIPLIER)
            },
            "compliance_info": {
                "pricing_source": "https://docs.claude.com/en/docs/about-claude/pricing",
                "last_updated": "2024-2025",
                "model_detected": usage_data.model != "claude-3-5-sonnet"
            }
        }