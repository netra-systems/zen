"""
Base Data Generator Configuration
Provides common constants and utilities for data generation
"""

import random
from typing import List, Optional
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


class DataGeneratorBase:
    """Base class with common configuration for data generators"""
    
    def __init__(self, seed: Optional[int] = None):
        if seed:
            random.seed(seed)
        
        self.models = [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, 
                       "gemini-pro", "gemini-ultra", "llama-70b", "mixtral-8x7b"]
        self.workload_types = ["chat", "completion", "embedding", "analysis", 
                              "rag_pipeline", "code_generation", "summarization"]
        self.components = ["api", "worker", "scheduler", "llm_manager", "agent_supervisor",
                          "websocket_handler", "database", "cache", "queue"]
        self.error_patterns = [
            "Connection timeout to {service}",
            "Rate limit exceeded for {model}",
            "Invalid response format from {component}",
            "Memory allocation failed: {size}MB requested",
            "Database connection pool exhausted",
            "Circuit breaker opened for {service}",
            "Token limit exceeded: {tokens} > {limit}",
            "Authentication failed for user {user_id}",
            "Retry limit reached for operation {op}",
            "Unexpected null value in {field}"
        ]