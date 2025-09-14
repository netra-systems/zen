"""Real LLM Test Suite Package.

This package contains all tests that require real LLM API integration.
NO MOCKS ALLOWED - all tests must use actual API calls.

Test Categories:
- API Integration: Direct API calls to OpenAI, Anthropic, Google
- Cost Tracking: Real cost monitoring and optimization validation
- Error Handling: Real error recovery, retries, and rate limiting
- Performance: Real performance SLAs and timing validation
- Streaming: Real streaming response testing

Business Value Justification (BVJ):
1. Segment: Enterprise ($347K+ MRR protection)
2. Business Goal: Validate real LLM performance and value creation
3. Value Impact: Ensures 20-50% cost reduction claims are accurate
4. Revenue Impact: Protects $347K+ MRR from LLM integration failures

IMPORTANT: All tests require valid API keys and will fail explicitly if not available.
"""

__version__ = "1.0.0"
__author__ = "Netra Engineering Team"

# Test categories for pytest markers
TEST_CATEGORIES = [
    "api_integration",
    "cost_tracking", 
    "error_handling",
    "performance",
    "streaming"
]

# Required environment variables for real LLM testing
REQUIRED_API_KEYS = [
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",  # Optional but recommended
    "ANTHROPIC_API_KEY"  # Optional but recommended
]
