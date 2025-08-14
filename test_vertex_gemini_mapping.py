"""Test script to verify Vertex AI and Gemini model mappings"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.schemas.llm_types import LLMProvider, LLMModel

def test_provider_mappings():
    """Test that all providers are defined correctly"""
    print("Testing LLM Provider Enums:")
    print("="*50)
    
    # Test providers
    assert LLMProvider.GOOGLE == "google", "Google provider not mapped correctly"
    assert LLMProvider.VERTEXAI == "vertexai", "VertexAI provider not mapped correctly"
    print("✓ Google provider maps to:", LLMProvider.GOOGLE)
    print("✓ VertexAI provider maps to:", LLMProvider.VERTEXAI)
    
    print("\nTesting LLM Model Enums:")
    print("="*50)
    
    # Test new Gemini models
    assert LLMModel.GEMINI_25_PRO == "gemini-2.5-pro", "Gemini 2.5 Pro not mapped correctly"
    assert LLMModel.GEMINI_25_FLASH == "gemini-2.5-flash", "Gemini 2.5 Flash not mapped correctly"
    assert LLMModel.GEMINI_20_FLASH == "gemini-2.0-flash", "Gemini 2.0 Flash not mapped correctly"
    
    print("✓ Gemini 2.5 Pro maps to:", LLMModel.GEMINI_25_PRO)
    print("✓ Gemini 2.5 Flash maps to:", LLMModel.GEMINI_25_FLASH)
    print("✓ Gemini 2.0 Flash maps to:", LLMModel.GEMINI_20_FLASH)
    
    # Test legacy models still exist
    assert LLMModel.GEMINI_PRO == "gemini-pro", "Legacy Gemini Pro missing"
    assert LLMModel.GEMINI_ULTRA == "gemini-ultra", "Legacy Gemini Ultra missing"
    print("✓ Legacy Gemini Pro still available:", LLMModel.GEMINI_PRO)
    print("✓ Legacy Gemini Ultra still available:", LLMModel.GEMINI_ULTRA)
    
    print("\n" + "="*50)
    print("✅ ALL TESTS PASSED!")
    print("="*50)
    
    return True

def test_llm_manager_handling():
    """Test that llm_manager can handle both google and vertexai providers"""
    from unittest.mock import MagicMock, patch
    from app.llm.llm_manager import LLMManager
    from app.schemas.Config import AppConfig, LLMConfig
    
    print("\nTesting LLM Manager Provider Handling:")
    print("="*50)
    
    # Create mock config
    mock_config = AppConfig()
    mock_config.llm_configs = {
        "google_test": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
            api_key="test-key"
        ),
        "vertexai_test": LLMConfig(
            provider="vertexai", 
            model_name="gemini-2.5-pro",
            api_key="test-key"
        )
    }
    
    manager = LLMManager(mock_config)
    
    # Mock the ChatGoogleGenerativeAI import
    with patch('app.llm.llm_manager.ChatGoogleGenerativeAI') as mock_chat:
        mock_chat.return_value = MagicMock()
        
        # Test google provider
        llm_google = manager.get_llm("google_test")
        assert llm_google is not None, "Google provider LLM not created"
        print("✓ Google provider creates LLM instance")
        
        # Test vertexai provider
        llm_vertex = manager.get_llm("vertexai_test")
        assert llm_vertex is not None, "VertexAI provider LLM not created"
        print("✓ VertexAI provider creates LLM instance")
        
        # Both should use ChatGoogleGenerativeAI
        assert mock_chat.call_count == 2, "Both providers should use ChatGoogleGenerativeAI"
        print("✓ Both providers use same underlying implementation")
    
    print("\n✅ LLM Manager tests passed!")
    
    return True

if __name__ == "__main__":
    try:
        test_provider_mappings()
        test_llm_manager_handling()
        print("\n🎉 All verification tests completed successfully!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)