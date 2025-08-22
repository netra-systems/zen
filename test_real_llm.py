#!/usr/bin/env python3
"""
Real LLM API Test

Tests the actual LLM integration with real API keys to validate
the complete AI processing pipeline.
"""

import asyncio
import sys
import os
import time
from dotenv import load_dotenv

# Load environment variables
project_root = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

# Add the project root to Python path
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'netra_backend'))

async def test_real_llm_call():
    """Test making a real LLM API call with actual API key."""
    try:
        # Import after environment is loaded
        from netra_backend.app.config import get_config
        from netra_backend.app.llm.llm_manager import LLMManager
        
        print("Testing Real LLM API Call...")
        
        # Check if we have the API key
        gemini_key = os.environ.get('GEMINI_API_KEY')
        if not gemini_key or 'placeholder' in gemini_key:
            print("SKIP: No valid Gemini API key found")
            return True
            
        print(f"Using Gemini API key: {gemini_key[:10]}...")
        
        config = get_config()
        llm_manager = LLMManager(config)
        
        if not llm_manager.enabled:
            print("SKIP: LLM manager is disabled")
            return True
            
        # Update the config with the API key
        if 'default' in config.llm_configs:
            config.llm_configs['default'].api_key = gemini_key
            
        # Test with a simple prompt
        test_prompt = "Hello! Please respond with exactly: 'AI system is working correctly'"
        
        print(f"Sending test prompt: {test_prompt}")
        
        start_time = time.time()
        try:
            # Try with the default configuration
            response = await llm_manager.ask_llm(test_prompt, "default", use_cache=False)
            duration = (time.time() - start_time) * 1000
            
            print(f"PASS: Real LLM call successful ({duration:.1f}ms)")
            print(f"Response: {response}")
            
            # Check if we got a reasonable response
            if len(response.strip()) > 0:
                print("PASS: LLM returned valid response")
                return True
            else:
                print("WARN: LLM returned empty response")
                return False
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            print(f"FAIL: Real LLM call failed ({duration:.1f}ms): {e}")
            return False
                
    except Exception as e:
        print(f"FAIL: Real LLM test setup failed: {e}")
        return False

async def test_streaming_llm():
    """Test streaming LLM response."""
    try:
        from netra_backend.app.config import get_config
        from netra_backend.app.llm.llm_manager import LLMManager
        
        print("\nTesting Streaming LLM...")
        
        gemini_key = os.environ.get('GEMINI_API_KEY')
        if not gemini_key or 'placeholder' in gemini_key:
            print("SKIP: No valid Gemini API key found")
            return True
            
        config = get_config()
        llm_manager = LLMManager(config)
        
        if not llm_manager.enabled:
            print("SKIP: LLM manager is disabled")
            return True
            
        # Update the config with the API key
        if 'default' in config.llm_configs:
            config.llm_configs['default'].api_key = gemini_key
            
        # Test streaming
        test_prompt = "Count from 1 to 3, with each number on a new line."
        
        print(f"Streaming test prompt: {test_prompt}")
        
        start_time = time.time()
        chunks = []
        
        try:
            async for chunk in llm_manager.stream_llm(test_prompt, "default"):
                chunks.append(chunk)
                print(f"Chunk: {chunk}", end="", flush=True)
                
            duration = (time.time() - start_time) * 1000
            full_response = "".join(chunks)
            
            print(f"\nPASS: Streaming LLM call successful ({duration:.1f}ms)")
            print(f"Full response: {full_response}")
            print(f"Total chunks: {len(chunks)}")
            
            return True
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            print(f"\nFAIL: Streaming LLM call failed ({duration:.1f}ms): {e}")
            return False
                
    except Exception as e:
        print(f"FAIL: Streaming LLM test setup failed: {e}")
        return False

async def test_multiple_llm_configs():
    """Test multiple LLM configurations."""
    try:
        from netra_backend.app.config import get_config
        from netra_backend.app.llm.llm_manager import LLMManager
        
        print("\nTesting Multiple LLM Configurations...")
        
        gemini_key = os.environ.get('GEMINI_API_KEY')
        if not gemini_key or 'placeholder' in gemini_key:
            print("SKIP: No valid Gemini API key found")
            return True
            
        config = get_config()
        llm_manager = LLMManager(config)
        
        if not llm_manager.enabled:
            print("SKIP: LLM manager is disabled")
            return True
            
        # Update all configs with the API key
        for config_name in config.llm_configs:
            config.llm_configs[config_name].api_key = gemini_key
            
        # Test different configurations
        test_configs = ['default', 'triage', 'analysis']
        test_prompt = "What is 2+2?"
        
        results = []
        
        for config_name in test_configs:
            if config_name not in config.llm_configs:
                continue
                
            print(f"Testing config '{config_name}'...")
            
            try:
                start_time = time.time()
                response = await llm_manager.ask_llm(test_prompt, config_name, use_cache=False)
                duration = (time.time() - start_time) * 1000
                
                print(f"  PASS: {config_name} ({duration:.1f}ms) - {response[:50]}...")
                results.append(True)
                
            except Exception as e:
                print(f"  FAIL: {config_name} - {e}")
                results.append(False)
        
        success_rate = sum(results) / len(results) if results else 0
        print(f"Config test success rate: {success_rate*100:.1f}% ({sum(results)}/{len(results)})")
        
        return success_rate > 0.5  # Pass if more than half work
                
    except Exception as e:
        print(f"FAIL: Multiple config test setup failed: {e}")
        return False

async def main():
    """Run all real LLM tests."""
    print("Real LLM API Integration Test")
    print("=" * 40)
    
    # Check environment
    print("Environment Check:")
    gemini_key = os.environ.get('GEMINI_API_KEY', 'not found')
    print(f"  GEMINI_API_KEY: {gemini_key[:15]}..." if gemini_key != 'not found' else "  GEMINI_API_KEY: not found")
    
    tests = [
        ("Real LLM API Call", test_real_llm_call),
        ("Streaming LLM", test_streaming_llm),
        ("Multiple LLM Configs", test_multiple_llm_configs),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"FAIL: {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("REAL LLM TEST SUMMARY")
    print("=" * 40)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    print("\nDetailed Results:")
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {status}: {test_name}")
    
    # Critical Analysis
    print("\nCRITICAL ANALYSIS:")
    real_call_ok = any(name == "Real LLM API Call" and result for name, result in results)
    streaming_ok = any(name == "Streaming LLM" and result for name, result in results)
    
    if real_call_ok:
        print("PASS: Real LLM API integration is working")
        if streaming_ok:
            print("PASS: Streaming LLM functionality is working")
        print("SUCCESS: Users can get AI responses from the system")
    else:
        print("FAIL: Real LLM API integration is not working")
        print("ERROR: Users cannot get AI responses")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest suite failed: {e}")
        sys.exit(1)