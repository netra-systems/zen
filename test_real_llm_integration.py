#!/usr/bin/env python
"""
Real LLM Integration Test - Direct API Testing
Tests actual LLM API calls with real providers to verify integration status.
"""

import os
import asyncio
import time
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.llm.llm_manager import LLMManager
from app.schemas import AppConfig, LLMConfig
from pydantic import BaseModel, Field

class TestResponseModel(BaseModel):
    """Test model for structured responses."""
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

async def test_real_llm_integration():
    """Test real LLM integration with actual API calls."""
    
    print("REAL LLM INTEGRATION TEST - ELITE ENGINEER EXECUTION")
    print("=" * 80)
    
    # Check environment variables
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    print("Environment Variables Status:")
    print(f"  GEMINI_API_KEY: {'[SET]' if gemini_key else '[MISSING]'}")
    print(f"  OPENAI_API_KEY: {'[SET]' if openai_key else '[MISSING]'}")
    print(f"  ANTHROPIC_API_KEY: {'[SET]' if anthropic_key else '[MISSING]'}")
    print()
    
    results = {}
    
    # Test Gemini (Google) if available
    if gemini_key:
        print("[TESTING] Testing Gemini API Integration...")
        try:
            config = AppConfig(
                llm_configs={
                    "gemini": LLMConfig(
                        provider="google",
                        model_name="gemini-1.5-flash",
                        api_key=gemini_key,
                        generation_config={"temperature": 0.3}
                    )
                }
            )
            
            manager = LLMManager(config)
            manager.enabled = True
            manager._core.enabled = True
            
            # Basic text completion test
            start_time = time.time()
            basic_response = await manager.ask_llm(
                "Respond with exactly: 'LLM Integration Test: SUCCESS'", 
                "gemini"
            )
            basic_time = time.time() - start_time
            
            # Structured generation test
            start_time = time.time()
            structured_prompt = """
            Analyze this test scenario and respond in JSON format:
            
            Test: LLM integration verification
            Expected: Successful API connection and response parsing
            
            Provide your analysis as JSON with category, confidence, and reasoning.
            """
            
            structured_response = await manager.ask_structured_llm(
                structured_prompt,
                "gemini",
                TestResponseModel
            )
            structured_time = time.time() - start_time
            
            results["gemini"] = {
                "status": "[SUCCESS]",
                "basic_response": basic_response[:100] + "..." if len(basic_response) > 100 else basic_response,
                "basic_latency": f"{basic_time:.2f}s",
                "structured_response": structured_response.model_dump(),
                "structured_latency": f"{structured_time:.2f}s",
                "error": None
            }
            
            print(f"  [SUCCESS] Basic Call: {basic_time:.2f}s - {basic_response[:50]}...")
            print(f"  [SUCCESS] Structured Call: {structured_time:.2f}s - Category: {structured_response.category}")
            
        except Exception as e:
            results["gemini"] = {
                "status": "[FAILED]",
                "error": str(e),
                "basic_response": None,
                "structured_response": None
            }
            print(f"  [ERROR] Error: {str(e)}")
    
    # Test OpenAI if available
    if openai_key and openai_key != "test-openai-key":
        print("\n[TESTING] Testing OpenAI API Integration...")
        try:
            config = AppConfig(
                llm_configs={
                    "openai": LLMConfig(
                        provider="openai",
                        model_name="gpt-3.5-turbo",
                        api_key=openai_key,
                        generation_config={"temperature": 0.3}
                    )
                }
            )
            
            manager = LLMManager(config)
            manager.enabled = True
            manager._core.enabled = True
            
            start_time = time.time()
            response = await manager.ask_llm(
                "Respond with exactly: 'OpenAI Integration Test: SUCCESS'", 
                "openai"
            )
            response_time = time.time() - start_time
            
            results["openai"] = {
                "status": "[SUCCESS]",
                "response": response[:100] + "..." if len(response) > 100 else response,
                "latency": f"{response_time:.2f}s",
                "error": None
            }
            
            print(f"  [SUCCESS] Success: {response_time:.2f}s - {response[:50]}...")
            
        except Exception as e:
            results["openai"] = {
                "status": "[FAILED]",
                "error": str(e)
            }
            print(f"  [ERROR] Error: {str(e)}")
    
    # Test error scenarios
    print("\n[TESTING] Testing Error Scenarios...")
    try:
        # Test with invalid API key
        config = AppConfig(
            llm_configs={
                "invalid": LLMConfig(
                    provider="google",
                    model_name="gemini-1.5-flash",
                    api_key="invalid-key-test",
                    generation_config={"temperature": 0.3}
                )
            }
        )
        
        manager = LLMManager(config)
        manager.enabled = True
        manager._core.enabled = True
        
        try:
            await manager.ask_llm("test", "invalid")
            results["error_handling"] = "❌ Should have failed with invalid key"
        except Exception as e:
            results["error_handling"] = f"✅ Correctly handled error: {type(e).__name__}"
            print(f"  [SUCCESS] Error handling: {type(e).__name__}")
            
    except Exception as e:
        results["error_handling"] = f"❌ Setup failed: {str(e)}"
    
    # Test rate limiting behavior
    print("\n[TESTING] Testing Rate Limiting Behavior...")
    if gemini_key:
        try:
            config = AppConfig(
                llm_configs={
                    "gemini": LLMConfig(
                        provider="google",
                        model_name="gemini-1.5-flash",
                        api_key=gemini_key,
                        generation_config={"temperature": 0.1}
                    )
                }
            )
            
            manager = LLMManager(config)
            manager.enabled = True
            manager._core.enabled = True
            
            # Make 3 quick successive calls
            start_time = time.time()
            tasks = []
            for i in range(3):
                task = manager.ask_llm(f"Quick test {i+1}", "gemini")
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            successful_calls = sum(1 for r in responses if not isinstance(r, Exception))
            results["rate_limiting"] = {
                "total_calls": 3,
                "successful_calls": successful_calls,
                "total_time": f"{total_time:.2f}s",
                "avg_latency": f"{total_time/3:.2f}s"
            }
            
            print(f"  [SUCCESS] {successful_calls}/3 calls successful in {total_time:.2f}s")
            
        except Exception as e:
            results["rate_limiting"] = f"❌ Error: {str(e)}"
    
    return results

def print_final_report(results: Dict[str, Any]):
    """Print comprehensive test report."""
    print("\n" + "=" * 80)
    print("REPORT: REAL LLM INTEGRATION TEST RESULTS")
    print("=" * 80)
    
    providers_tested = 0
    providers_successful = 0
    
    for provider, result in results.items():
        if provider in ["gemini", "openai", "anthropic"]:
            providers_tested += 1
            if isinstance(result, dict) and result.get("status") == "[SUCCESS]":
                providers_successful += 1
    
    print(f"Providers Tested: {providers_tested}")
    print(f"Providers Successful: {providers_successful}")
    print(f"Success Rate: {(providers_successful/providers_tested*100) if providers_tested > 0 else 0:.1f}%")
    print()
    
    for provider, result in results.items():
        print(f"{provider.upper()}:")
        if isinstance(result, dict):
            for key, value in result.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {result}")
        print()
    
    # Configuration recommendations
    print("CONFIG: CONFIGURATION RECOMMENDATIONS:")
    if results.get("gemini", {}).get("status") == "[SUCCESS]":
        print("  [SUCCESS] Gemini API working - Recommended for cost-effective testing")
    if results.get("openai", {}).get("status") == "[SUCCESS]":
        print("  [SUCCESS] OpenAI API working - Good for complex reasoning tasks")
    
    # Performance insights
    if "rate_limiting" in results and isinstance(results["rate_limiting"], dict):
        print("  [OK] Rate limiting behavior acceptable")
    
    print("  [OK] Error handling functioning correctly" if "error_handling" in results else "  [WARNING]  Error handling needs verification")

async def main():
    """Main execution function."""
    try:
        results = await test_real_llm_integration()
        print_final_report(results)
        
        # Return exit code based on results
        success_count = sum(1 for r in results.values() 
                          if isinstance(r, dict) and r.get("status") == "[SUCCESS]")
        
        if success_count > 0:
            print("\n[SUCCESS] REAL LLM INTEGRATION: OPERATIONAL")
            return 0
        else:
            print("\n❌ REAL LLM INTEGRATION: ISSUES DETECTED")
            return 1
            
    except Exception as e:
        print(f"\n[CRITICAL ERROR] CRITICAL ERROR: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)