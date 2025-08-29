#!/usr/bin/env python
"""Verify that LLM configuration is properly set to use Gemini 2.5 Pro as default for tests."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def verify_llm_configuration():
    """Verify that the LLM configuration is properly set."""
    print("=" * 60)
    print("LLM CONFIGURATION VERIFICATION")
    print("=" * 60)
    
    # Check test framework configuration
    from test_framework.llm_config_manager import get_llm_config_manager, configure_llm_testing, LLMTestMode
    
    manager = get_llm_config_manager()
    
    # Check default model in configure_llm_testing
    config = configure_llm_testing(mode=LLMTestMode.REAL)
    print(f"\n1. Test Runner Default Model: {config['model']}")
    assert config['model'] == "gemini-2.5-pro", f"Expected gemini-2.5-pro, got {config['model']}"
    print("   [OK] Test runner uses gemini-2.5-pro by default")
    
    # Check LLM defaults
    from netra_backend.app.llm.llm_defaults import LLMModel
    
    test_default = LLMModel.get_test_default()
    print(f"\n2. LLMModel Test Default: {test_default.value}")
    assert test_default.value == "gemini-2.5-pro", f"Expected gemini-2.5-pro, got {test_default.value}"
    print("   [OK] LLMModel.get_test_default() returns gemini-2.5-pro")
    
    # Check when TESTING is set
    os.environ['TESTING'] = 'true'
    default_with_testing = LLMModel.get_default()
    print(f"\n3. LLMModel Default (with TESTING=true): {default_with_testing.value}")
    assert default_with_testing.value == "gemini-2.5-pro", f"Expected gemini-2.5-pro, got {default_with_testing.value}"
    print("   [OK] LLMModel.get_default() returns gemini-2.5-pro when TESTING=true")
    
    # Check test environment setup
    from test_framework.test_environment_setup import TestSession
    
    session = TestSession(
        session_id="test",
        test_level="unit"
    )
    print(f"\n4. TestSession Default Model: {session.llm_model}")
    assert session.llm_model == "gemini-2.5-pro", f"Expected gemini-2.5-pro, got {session.llm_model}"
    print("   [OK] TestSession uses gemini-2.5-pro by default")
    
    # Check model configuration exists
    model_config = manager.get_model_config("gemini-2.5-pro")
    print(f"\n5. Gemini 2.5 Pro Configuration:")
    print(f"   - Name: {model_config.name}")
    print(f"   - Provider: {model_config.provider.value}")
    print(f"   - Max Tokens: {model_config.max_tokens}")
    print(f"   - Cost per 1k tokens: ${model_config.cost_per_1k_tokens}")
    assert model_config.name == "gemini-2.5-pro", f"Expected gemini-2.5-pro, got {model_config.name}"
    print("   [OK] Gemini 2.5 Pro is properly configured")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] ALL CHECKS PASSED!")
    print("Gemini 2.5 Pro is correctly configured as the default LLM for tests.")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = verify_llm_configuration()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        print(f"\n[FAIL] VERIFICATION FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)