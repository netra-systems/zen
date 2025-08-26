from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig

DEFAULT_CONFIG = '''
generation_settings:
  # The distribution of trace types to generate.
  # These values should sum to 1.0.
  trace_distribution:
    simple_chat: 0.4
    rag_pipeline: 0.3
    tool_use: 0.2
    failed_request: 0.05
    multi_turn_tool_use: 0.05

realism:
  # A pool of realistic application and service names.
  applications:
    - app_name: "customer-support-chatbot"
      services: ["chat-responder", "intent-classifier", "history-summarizer"]
    - app_name: "internal-doc-search"
      services: ["query-parser", "retrieval-engine", "answer-generator"]
    - app_name: "marketing-copy-generator"
      services: ["headline-generator", "seo-analyzer", "copy-writer"]

  # A pool of realistic model configurations.
  # Pricing is in USD per 1M tokens (prompt, completion).
  models:
    - { provider: "openai", name: "gpt-4o", pricing: [5.00, 15.00] }
    - { provider: "anthropic", name: LLMModel.GEMINI_2_5_FLASH.value, pricing: [15.00, 75.00] }
    - { provider: "google", name: "gemini-2.0-flash", pricing: [0.35, 0.70] }
    - { provider: "vllm", name: "llama-3.1-70b-instruct", pricing: [0.50, 0.50] }
'''
