"""Token Counter for tracking LLM token usage and costs."""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


class TokenType(Enum):
    """Types of tokens."""
    INPUT = "input"
    OUTPUT = "output"
    TOTAL = "total"


@dataclass
class TokenCount:
    """Token count result."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    model: str
    timestamp: datetime
    cost_estimate: Decimal = Decimal("0.00")
    metadata: Optional[Dict[str, Any]] = None


class TokenCounter:
    """Counts tokens for various LLM models and calculates costs."""
    
    def __init__(self):
        """Initialize token counter."""
        # Token pricing per 1K tokens (in USD)
        self.model_pricing = {
            # OpenAI GPT models
            "gpt-4": {"input": Decimal("0.03"), "output": Decimal("0.06")},
            "gpt-4-turbo": {"input": Decimal("0.01"), "output": Decimal("0.03")},
            "gpt-3.5-turbo": {"input": Decimal("0.0015"), "output": Decimal("0.002")},
            "gpt-3.5-turbo-instruct": {"input": Decimal("0.0015"), "output": Decimal("0.002")},
            
            # Anthropic Claude models
            "claude-3-opus": {"input": Decimal("0.015"), "output": Decimal("0.075")},
            "claude-3-sonnet": {"input": Decimal("0.003"), "output": Decimal("0.015")},
            "claude-3-haiku": {"input": Decimal("0.00025"), "output": Decimal("0.00125")},
            "claude-instant": {"input": Decimal("0.0008"), "output": Decimal("0.0024")},
            
            # Google models
            "gemini-pro": {"input": Decimal("0.0005"), "output": Decimal("0.0015")},
            "palm-2": {"input": Decimal("0.0005"), "output": Decimal("0.0015")},
            
            # Default pricing for unknown models
            "default": {"input": Decimal("0.001"), "output": Decimal("0.002")}
        }
        
        # Token counting patterns and multipliers
        self.token_estimators = {
            # Rough estimation: 1 token ≈ 4 characters for English
            "character_based": lambda text: len(text) // 4,
            
            # Word-based estimation: 1 token ≈ 0.75 words
            "word_based": lambda text: int(len(text.split()) / 0.75),
            
            # More sophisticated estimation
            "advanced": self._advanced_token_estimate
        }
        
        self.enabled = True
        
        # Statistics
        self.stats = {
            "total_counts_performed": 0,
            "total_tokens_counted": 0,
            "total_cost_calculated": Decimal("0.00"),
            "models_processed": set(),
            "counts_by_model": {},
            "average_tokens_per_request": 0.0
        }
    
    def count_tokens(self, text: str, model: str = "gpt-3.5-turbo", 
                    token_type: TokenType = TokenType.INPUT,
                    estimator: str = "advanced") -> int:
        """Count tokens in text for a specific model."""
        if not self.enabled:
            return 0
        
        if not text:
            return 0
        
        # Use appropriate estimator
        estimator_func = self.token_estimators.get(estimator, self.token_estimators["advanced"])
        token_count = estimator_func(text)
        
        # Update statistics
        self.stats["total_counts_performed"] += 1
        self.stats["total_tokens_counted"] += token_count
        self.stats["models_processed"].add(model)
        
        if model not in self.stats["counts_by_model"]:
            self.stats["counts_by_model"][model] = {"requests": 0, "tokens": 0}
        
        self.stats["counts_by_model"][model]["requests"] += 1
        self.stats["counts_by_model"][model]["tokens"] += token_count
        
        # Update average
        self.stats["average_tokens_per_request"] = (
            self.stats["total_tokens_counted"] / max(self.stats["total_counts_performed"], 1)
        )
        
        return token_count
    
    def count_conversation_tokens(self, messages: List[Dict[str, str]], 
                                model: str = "gpt-3.5-turbo") -> TokenCount:
        """Count tokens for a conversation (list of messages)."""
        if not self.enabled:
            return TokenCount(0, 0, 0, model, datetime.now(timezone.utc))
        
        input_tokens = 0
        output_tokens = 0
        
        for message in messages:
            content = message.get("content", "")
            role = message.get("role", "user")
            
            token_count = self.count_tokens(content, model)
            
            if role in ["user", "system"]:
                input_tokens += token_count
            elif role == "assistant":
                output_tokens += token_count
            else:
                # Unknown role, count as input
                input_tokens += token_count
        
        total_tokens = input_tokens + output_tokens
        cost_estimate = self.calculate_cost(input_tokens, output_tokens, model)
        
        # Update cost statistics
        self.stats["total_cost_calculated"] += cost_estimate
        
        return TokenCount(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            model=model,
            timestamp=datetime.now(timezone.utc),
            cost_estimate=cost_estimate
        )
    
    def calculate_cost(self, input_tokens: int, output_tokens: int, 
                      model: str = "gpt-3.5-turbo") -> Decimal:
        """Calculate cost for token usage."""
        # Get pricing for model
        pricing = self.model_pricing.get(model, self.model_pricing["default"])
        
        # Calculate cost per 1K tokens
        input_cost = (Decimal(str(input_tokens)) / 1000) * pricing["input"]
        output_cost = (Decimal(str(output_tokens)) / 1000) * pricing["output"]
        
        total_cost = input_cost + output_cost
        return total_cost.quantize(Decimal("0.000001"))  # 6 decimal places
    
    def estimate_cost_for_text(self, text: str, model: str = "gpt-3.5-turbo",
                              include_response: bool = True, 
                              response_ratio: float = 0.3) -> Decimal:
        """Estimate cost for processing text, optionally including response."""
        input_tokens = self.count_tokens(text, model)
        
        if include_response:
            # Estimate response tokens as a ratio of input
            output_tokens = int(input_tokens * response_ratio)
        else:
            output_tokens = 0
        
        return self.calculate_cost(input_tokens, output_tokens, model)
    
    def _advanced_token_estimate(self, text: str) -> int:
        """More sophisticated token estimation."""
        if not text:
            return 0
        
        # Clean and normalize text
        text = text.strip()
        
        # Count different types of tokens
        
        # 1. Word tokens (split by whitespace)
        words = text.split()
        word_tokens = len(words)
        
        # 2. Punctuation and special characters
        punctuation_count = len(re.findall(r'[^\w\s]', text))
        
        # 3. Numbers (often tokenized differently)
        number_count = len(re.findall(r'\d+', text))
        
        # 4. Special handling for common patterns
        # URLs, emails, etc. tend to be multiple tokens
        url_count = len(re.findall(r'https?://\S+', text))
        email_count = len(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
        
        # Estimate total tokens
        estimated_tokens = (
            word_tokens +  # Base word count
            (punctuation_count * 0.5) +  # Punctuation is often separate tokens
            (number_count * 0.3) +  # Numbers may be split
            (url_count * 3) +  # URLs are typically multiple tokens
            (email_count * 2)  # Emails are typically 2-3 tokens
        )
        
        # Apply a correction factor based on text characteristics
        if len(text) > 1000:
            # Longer texts tend to have more efficient tokenization
            estimated_tokens *= 0.9
        
        return max(1, int(estimated_tokens))
    
    def get_model_pricing(self, model: Optional[str] = None) -> Dict[str, Any]:
        """Get pricing information for models."""
        if model:
            return self.model_pricing.get(model, self.model_pricing["default"])
        return {k: dict(v) for k, v in self.model_pricing.items()}
    
    def update_model_pricing(self, model: str, input_price: Decimal, 
                           output_price: Decimal) -> None:
        """Update pricing for a model."""
        self.model_pricing[model] = {
            "input": input_price,
            "output": output_price
        }
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported models."""
        return [model for model in self.model_pricing.keys() if model != "default"]
    
    def compare_model_costs(self, text: str, models: Optional[List[str]] = None) -> Dict[str, Decimal]:
        """Compare costs across different models for the same text."""
        if models is None:
            models = self.get_supported_models()
        
        comparisons = {}
        for model in models:
            cost = self.estimate_cost_for_text(text, model)
            comparisons[model] = cost
        
        return comparisons
    
    def get_cheapest_model(self, text: str, 
                          models: Optional[List[str]] = None) -> Tuple[str, Decimal]:
        """Find the cheapest model for processing text."""
        comparisons = self.compare_model_costs(text, models)
        
        if not comparisons:
            return "default", Decimal("0.00")
        
        cheapest_model = min(comparisons, key=comparisons.get)
        cheapest_cost = comparisons[cheapest_model]
        
        return cheapest_model, cheapest_cost
    
    def analyze_usage_patterns(self) -> Dict[str, Any]:
        """Analyze token usage patterns and provide insights."""
        total_requests = self.stats["total_counts_performed"]
        total_tokens = self.stats["total_tokens_counted"]
        
        if total_requests == 0:
            return {"message": "No usage data available"}
        
        # Model usage analysis
        model_analysis = []
        for model, data in self.stats["counts_by_model"].items():
            percentage = (data["requests"] / total_requests) * 100
            avg_tokens = data["tokens"] / max(data["requests"], 1)
            
            model_analysis.append({
                "model": model,
                "requests": data["requests"],
                "tokens": data["tokens"],
                "percentage_of_requests": round(percentage, 2),
                "average_tokens_per_request": round(avg_tokens, 2)
            })
        
        # Sort by usage
        model_analysis.sort(key=lambda x: x["requests"], reverse=True)
        
        return {
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "average_tokens_per_request": round(self.stats["average_tokens_per_request"], 2),
            "total_estimated_cost": float(self.stats["total_cost_calculated"]),
            "model_usage": model_analysis,
            "most_used_model": model_analysis[0]["model"] if model_analysis else None
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get token counter statistics."""
        return {
            "enabled": self.enabled,
            "total_counts_performed": self.stats["total_counts_performed"],
            "total_tokens_counted": self.stats["total_tokens_counted"],
            "total_cost_calculated": float(self.stats["total_cost_calculated"]),
            "unique_models_processed": len(self.stats["models_processed"]),
            "average_tokens_per_request": self.stats["average_tokens_per_request"],
            "supported_models": len(self.get_supported_models()),
            "estimators_available": len(self.token_estimators)
        }
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {
            "total_counts_performed": 0,
            "total_tokens_counted": 0,
            "total_cost_calculated": Decimal("0.00"),
            "models_processed": set(),
            "counts_by_model": {},
            "average_tokens_per_request": 0.0
        }
    
    def disable(self) -> None:
        """Disable token counter."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable token counter."""
        self.enabled = True
