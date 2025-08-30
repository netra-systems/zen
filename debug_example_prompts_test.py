#!/usr/bin/env python3
"""Debug script for example prompts test"""
import os
import asyncio
from tests.e2e.test_example_prompts_e2e_real_llm import TestExamplePromptsData

def debug_test():
    print(f"ENABLE_REAL_LLM_TESTING env var: {os.getenv('ENABLE_REAL_LLM_TESTING', 'NOT_SET')}")
    print(f"Use real LLM result: {os.getenv('ENABLE_REAL_LLM_TESTING', 'false').lower() == 'true'}")
    
    test_cases = TestExamplePromptsData.get_all_test_cases()
    print(f"Found {len(test_cases)} test cases")
    
    first_case = test_cases[0]
    print(f"First test case: {first_case.prompt_id} - {first_case.category}")
    print(f"Expected agents: {first_case.expected_agents}")

if __name__ == "__main__":
    debug_test()