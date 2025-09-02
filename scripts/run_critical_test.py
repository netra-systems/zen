#!/usr/bin/env python
"""Script to run critical agent pipeline test with proper environment configuration."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from shared.isolated_environment import get_env

# Load .env file with override to ensure our values take precedence
env = get_env()
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path, override=True)

# Ensure GEMINI_API_KEY is set from .env
gemini_key = get_env().get('GEMINI_API_KEY')
if not get_env().get('GEMINI_API_KEY'):
    env.set('GEMINI_API_KEY', gemini_key, "test")
    print(f"Set GEMINI_API_KEY directly")

# Set all possible API key environment variables that might be needed
env.set('TEST_GOOGLE_API_KEY', gemini_key, "test")
env.set('TEST_GEMINI_API_KEY', gemini_key, "test")
env.set('GOOGLE_API_KEY', gemini_key, "test")  # Some code might look for this

print(f"Set all Google/Gemini API key variants")

# Enable real LLM testing
env.set('ENABLE_REAL_LLM_TESTING', 'true', "test")
env.set('TEST_LLM_MODE', 'real', "test")
env.set('USE_REAL_LLM', 'true', "test")
env.set('TEST_USE_REAL_LLM', 'true', "test")

# Set environment to testing to ensure config loads properly
env.set('ENVIRONMENT', 'testing', "test")

# Print configuration
print("\nEnvironment configuration:")
print(f"  ENVIRONMENT: {get_env().get('ENVIRONMENT')}")
print(f"  GEMINI_API_KEY: {'Set' if get_env().get('GEMINI_API_KEY') else 'Not set'}")
print(f"  GOOGLE_API_KEY: {'Set' if get_env().get('GOOGLE_API_KEY') else 'Not set'}")
print(f"  TEST_GOOGLE_API_KEY: {'Set' if get_env().get('TEST_GOOGLE_API_KEY') else 'Not set'}")
print(f"  TEST_GEMINI_API_KEY: {'Set' if get_env().get('TEST_GEMINI_API_KEY') else 'Not set'}")
print(f"  ENABLE_REAL_LLM_TESTING: {get_env().get('ENABLE_REAL_LLM_TESTING')}")
print(f"  TEST_LLM_MODE: {get_env().get('TEST_LLM_MODE')}")
print()

# Run pytest with the critical test
import pytest
sys.exit(pytest.main([
    'tests/e2e/test_agent_pipeline_critical.py',
    '-v',
    '--tb=short'
]))
