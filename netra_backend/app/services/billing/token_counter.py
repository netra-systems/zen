"""Token Counter for tracking LLM token usage and costs."""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig



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
            LLMModel.GEMINI_2_5_FLASH.value: {"input": Decimal("0.03"), "output": Decimal("0.06")},
            LLMModel.GEMINI_2_5_FLASH.value: {"input": Decimal("0.01"), "output": Decimal("0.03")},
            LLMModel.GEMINI_2_5_FLASH.value: {"input": Decimal("0.0015"), "output": Decimal("0.002")},
            "gpt-3.5-turbo-instruct": {"input": Decimal("0.0015"), "output": Decimal("0.002")},
            
            # Anthropic Claude models
            LLMModel.GEMINI_2_5_FLASH.value: {"input": Decimal("0.015"), "output": Decimal("0.075")},
            LLMModel.GEMINI_2_5_FLASH.value: {"input": Decimal("0.003"), "output": Decimal("0.015")},
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
            # Rough estimation: 1 token [U+2248] 4 characters for English
            "character_based": lambda text: len(text) // 4,
            
            # Word-based estimation: 1 token [U+2248] 0.75 words
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
    
    def count_tokens(self, text: str, model: str = LLMModel.GEMINI_2_5_FLASH.value, 
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
                                model: str = LLMModel.GEMINI_2_5_FLASH.value) -> TokenCount:
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
                      model: str = LLMModel.GEMINI_2_5_FLASH.value) -> Decimal:
        """Calculate cost for token usage."""
        # Get pricing for model
        pricing = self.model_pricing.get(model, self.model_pricing["default"])
        
        # Calculate cost per 1K tokens
        input_cost = (Decimal(str(input_tokens)) / 1000) * pricing["input"]
        output_cost = (Decimal(str(output_tokens)) / 1000) * pricing["output"]
        
        total_cost = input_cost + output_cost
        return total_cost.quantize(Decimal("0.000001"))  # 6 decimal places
    
    def estimate_cost_for_text(self, text: str, model: str = LLMModel.GEMINI_2_5_FLASH.value,
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
    
    def optimize_prompt(self, prompt: str, target_reduction_percent: int = 20, 
                       model: str = LLMModel.GEMINI_2_5_FLASH.value) -> Dict[str, Any]:
        """Optimize prompt to reduce token usage while preserving intent.
        
        Args:
            prompt: The original prompt text
            target_reduction_percent: Target percentage reduction (e.g., 20 for 20%)
            model: Model to optimize for
            
        Returns:
            Dictionary with optimization results including optimized prompt and metrics
        """
        if not prompt or not prompt.strip():
            return {
                "original_prompt": prompt,
                "optimized_prompt": prompt,
                "original_tokens": 0,
                "optimized_tokens": 0,
                "tokens_saved": 0,
                "reduction_percent": 0.0,
                "cost_savings": Decimal("0.00"),
                "optimization_applied": []
            }
        
        original_tokens = self.count_tokens(prompt, model)
        original_cost = self.estimate_cost_for_text(prompt, model, include_response=False)
        
        optimized_prompt = prompt
        optimizations_applied = []
        
        # 1. Remove redundant whitespace
        if len(re.findall(r'\s{2,}', optimized_prompt)) > 0:
            optimized_prompt = re.sub(r'\s{2,}', ' ', optimized_prompt)
            optimizations_applied.append("whitespace_normalization")
        
        # 2. Remove redundant phrases
        redundant_phrases = [
            r'\bplease\s+',
            r'\bkindly\s+', 
            r'\bi would like you to\s+',
            r'\bcan you please\s+',
            r'\bcould you\s+',
            r'\bit would be great if\s+'
        ]
        for pattern in redundant_phrases:
            if re.search(pattern, optimized_prompt, re.IGNORECASE):
                optimized_prompt = re.sub(pattern, '', optimized_prompt, flags=re.IGNORECASE)
                optimizations_applied.append("redundant_phrases")
                break
        
        # 3. Convert verbose expressions to concise equivalents
        replacements = {
            r'\bin order to\b': 'to',
            r'\bdue to the fact that\b': 'because',
            r'\bfor the purpose of\b': 'for',
            r'\bin the event that\b': 'if',
            r'\bas a result of\b': 'because',
            r'\bgive consideration to\b': 'consider',
            r'\bmake an assumption\b': 'assume'
        }
        for verbose, concise in replacements.items():
            if re.search(verbose, optimized_prompt, re.IGNORECASE):
                optimized_prompt = re.sub(verbose, concise, optimized_prompt, flags=re.IGNORECASE)
                if "verbose_replacements" not in optimizations_applied:
                    optimizations_applied.append("verbose_replacements")
        
        # 4. Remove excessive examples if present
        example_patterns = [
            r'\bfor example:.*?(?=\n|$)',
            r'\be\.g\.:.*?(?=\n|$)',
            r'\bsuch as:.*?(?=\n|$)'
        ]
        for pattern in example_patterns:
            matches = re.findall(pattern, optimized_prompt, re.IGNORECASE | re.DOTALL)
            if len(matches) > 2:  # Keep only first 2 examples
                optimized_prompt = re.sub(pattern, '', optimized_prompt, count=len(matches)-2, flags=re.IGNORECASE | re.DOTALL)
                optimizations_applied.append("example_reduction")
        
        # 5. Clean up any multiple spaces created by optimizations
        optimized_prompt = re.sub(r'\s{2,}', ' ', optimized_prompt).strip()
        
        # Calculate final metrics
        optimized_tokens = self.count_tokens(optimized_prompt, model)
        tokens_saved = original_tokens - optimized_tokens
        reduction_percent = (tokens_saved / max(original_tokens, 1)) * 100
        
        optimized_cost = self.estimate_cost_for_text(optimized_prompt, model, include_response=False)
        cost_savings = original_cost - optimized_cost
        
        return {
            "original_prompt": prompt,
            "optimized_prompt": optimized_prompt,
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "tokens_saved": tokens_saved,
            "reduction_percent": round(reduction_percent, 2),
            "cost_savings": cost_savings,
            "optimization_applied": optimizations_applied,
            "model": model,
            "target_achieved": reduction_percent >= target_reduction_percent
        }
    
    def track_agent_usage(self, agent_name: str, input_tokens: int, output_tokens: int,
                          model: str = LLMModel.GEMINI_2_5_FLASH.value,
                          operation_type: str = "execution") -> Dict[str, Any]:
        """Track token usage for a specific agent.
        
        Args:
            agent_name: Name of the agent
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            model: Model used for the operation
            operation_type: Type of operation (execution, thinking, tool_use, etc.)
            
        Returns:
            Dictionary with tracking results and cumulative metrics
        """
        if not self.enabled:
            return {"tracking_enabled": False}
        
        # Initialize agent tracking if needed
        if not hasattr(self, 'agent_usage_stats'):
            self.agent_usage_stats = {}
        
        if agent_name not in self.agent_usage_stats:
            self.agent_usage_stats[agent_name] = {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost": Decimal("0.00"),
                "operations_count": 0,
                "models_used": set(),
                "operation_types": {},
                "first_seen": datetime.now(timezone.utc),
                "last_seen": datetime.now(timezone.utc)
            }
        
        agent_stats = self.agent_usage_stats[agent_name]
        
        # Calculate cost for this operation
        operation_cost = self.calculate_cost(input_tokens, output_tokens, model)
        
        # Update agent statistics
        agent_stats["total_input_tokens"] += input_tokens
        agent_stats["total_output_tokens"] += output_tokens
        agent_stats["total_cost"] += operation_cost
        agent_stats["operations_count"] += 1
        agent_stats["models_used"].add(model)
        agent_stats["last_seen"] = datetime.now(timezone.utc)
        
        # Track operation types
        if operation_type not in agent_stats["operation_types"]:
            agent_stats["operation_types"][operation_type] = {
                "count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": Decimal("0.00")
            }
        
        op_stats = agent_stats["operation_types"][operation_type]
        op_stats["count"] += 1
        op_stats["input_tokens"] += input_tokens
        op_stats["output_tokens"] += output_tokens
        op_stats["cost"] += operation_cost
        
        # Calculate efficiency metrics
        total_tokens = input_tokens + output_tokens
        avg_tokens_per_operation = (
            (agent_stats["total_input_tokens"] + agent_stats["total_output_tokens"]) / 
            agent_stats["operations_count"]
        )
        
        # Return tracking result
        return {
            "tracking_enabled": True,
            "agent_name": agent_name,
            "operation_type": operation_type,
            "current_operation": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost": float(operation_cost),
                "model": model
            },
            "cumulative_stats": {
                "total_operations": agent_stats["operations_count"],
                "total_input_tokens": agent_stats["total_input_tokens"],
                "total_output_tokens": agent_stats["total_output_tokens"],
                "total_tokens": agent_stats["total_input_tokens"] + agent_stats["total_output_tokens"],
                "total_cost": float(agent_stats["total_cost"]),
                "average_tokens_per_operation": round(avg_tokens_per_operation, 2),
                "models_used": list(agent_stats["models_used"]),
                "operation_types": {k: dict(v) for k, v in agent_stats["operation_types"].items()}
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_optimization_suggestions(self, agent_usage_data: Optional[Dict[str, Any]] = None,
                                   cost_threshold: Optional[Decimal] = None) -> List[Dict[str, Any]]:
        """Get optimization suggestions based on usage patterns.
        
        Args:
            agent_usage_data: Optional agent usage data (if None, uses all tracked agents)
            cost_threshold: Optional cost threshold for flagging expensive operations
            
        Returns:
            List of optimization suggestions with priorities and potential savings
        """
        suggestions = []
        
        if not hasattr(self, 'agent_usage_stats') or not self.agent_usage_stats:
            return [{
                "type": "no_data",
                "priority": "low",
                "title": "No Usage Data Available",
                "description": "Start tracking agent usage to get optimization suggestions.",
                "potential_savings": "N/A"
            }]
        
        # Set default cost threshold
        if cost_threshold is None:
            cost_threshold = Decimal("1.00")  # $1.00 default threshold
        
        # Analyze all agents or specific agent
        agents_to_analyze = (
            {agent_usage_data["agent_name"]: self.agent_usage_stats[agent_usage_data["agent_name"]]}
            if agent_usage_data and "agent_name" in agent_usage_data
            else self.agent_usage_stats
        )
        
        for agent_name, stats in agents_to_analyze.items():
            agent_cost = stats["total_cost"]
            avg_tokens = (
                (stats["total_input_tokens"] + stats["total_output_tokens"]) / 
                max(stats["operations_count"], 1)
            )
            
            # High cost agent suggestion
            if agent_cost > cost_threshold:
                suggestions.append({
                    "type": "high_cost_agent",
                    "priority": "high",
                    "title": f"High Cost Agent: {agent_name}",
                    "description": f"Agent has incurred ${float(agent_cost):.4f} in costs across {stats['operations_count']} operations.",
                    "recommendation": "Consider prompt optimization or switching to more cost-effective models.",
                    "agent_name": agent_name,
                    "current_cost": float(agent_cost),
                    "potential_savings": f"${float(agent_cost * Decimal('0.2')):.4f} (20% reduction)"
                })
            
            # High token usage suggestion
            if avg_tokens > 2000:
                suggestions.append({
                    "type": "high_token_usage",
                    "priority": "medium",
                    "title": f"High Token Usage: {agent_name}",
                    "description": f"Agent averages {avg_tokens:.0f} tokens per operation.",
                    "recommendation": "Review prompts for verbosity and consider prompt optimization techniques.",
                    "agent_name": agent_name,
                    "average_tokens": round(avg_tokens, 2),
                    "potential_savings": f"{avg_tokens * 0.15:.0f} tokens per operation (15% reduction)"
                })
            
            # Model efficiency suggestions
            models_used = list(stats["models_used"])
            if len(models_used) > 1:
                # Find cheapest model for comparison
                cheapest_model, cheapest_cost = self.get_cheapest_model("sample text for comparison", models_used)
                
                suggestions.append({
                    "type": "model_optimization",
                    "priority": "medium",
                    "title": f"Model Optimization: {agent_name}",
                    "description": f"Agent uses {len(models_used)} different models. Consider standardizing on cost-effective options.",
                    "recommendation": f"Consider using {cheapest_model} for cost savings.",
                    "agent_name": agent_name,
                    "models_used": models_used,
                    "recommended_model": cheapest_model,
                    "potential_savings": "10-30% cost reduction"
                })
            
            # Operation type analysis
            op_types = stats.get("operation_types", {})
            for op_type, op_stats in op_types.items():
                if op_stats["cost"] > cost_threshold * Decimal("0.5"):  # 50% of threshold per operation type
                    suggestions.append({
                        "type": "expensive_operation",
                        "priority": "medium",
                        "title": f"Expensive Operation Type: {agent_name}.{op_type}",
                        "description": f"Operation type '{op_type}' has cost ${float(op_stats['cost']):.4f} across {op_stats['count']} calls.",
                        "recommendation": "Optimize prompts for this operation type or cache frequent results.",
                        "agent_name": agent_name,
                        "operation_type": op_type,
                        "operation_cost": float(op_stats["cost"]),
                        "potential_savings": f"${float(op_stats['cost'] * Decimal('0.25')):.4f} (25% reduction)"
                    })
        
        # Global suggestions
        total_cost = sum(Decimal(str(stats["total_cost"])) for stats in self.agent_usage_stats.values())
        if total_cost > cost_threshold * 5:  # 5x threshold for global suggestions
            suggestions.append({
                "type": "global_optimization",
                "priority": "high",
                "title": "Overall Cost Optimization",
                "description": f"Total system cost is ${float(total_cost):.4f} across all agents.",
                "recommendation": "Implement systematic prompt optimization and consider result caching.",
                "total_cost": float(total_cost),
                "potential_savings": f"${float(total_cost * Decimal('0.2')):.4f} (20% system-wide reduction)"
            })
        
        # Sort suggestions by priority
        priority_order = {"high": 3, "medium": 2, "low": 1}
        suggestions.sort(key=lambda x: priority_order.get(x["priority"], 0), reverse=True)
        
        return suggestions
    
    def get_agent_usage_summary(self) -> Dict[str, Any]:
        """Get summary of agent usage statistics.
        
        Returns:
            Dictionary with comprehensive agent usage summary
        """
        if not hasattr(self, 'agent_usage_stats') or not self.agent_usage_stats:
            return {
                "agents_tracked": 0,
                "total_operations": 0,
                "total_cost": 0.0,
                "total_tokens": 0,
                "message": "No agent usage data available"
            }
        
        total_operations = sum(stats["operations_count"] for stats in self.agent_usage_stats.values())
        total_cost = sum(stats["total_cost"] for stats in self.agent_usage_stats.values())
        total_tokens = sum(
            stats["total_input_tokens"] + stats["total_output_tokens"]
            for stats in self.agent_usage_stats.values()
        )
        
        # Find most expensive agent
        most_expensive = max(
            self.agent_usage_stats.items(),
            key=lambda x: x[1]["total_cost"]
        ) if self.agent_usage_stats else (None, {"total_cost": 0})
        
        # Find most active agent
        most_active = max(
            self.agent_usage_stats.items(),
            key=lambda x: x[1]["operations_count"]
        ) if self.agent_usage_stats else (None, {"operations_count": 0})
        
        return {
            "agents_tracked": len(self.agent_usage_stats),
            "total_operations": total_operations,
            "total_cost": float(total_cost),
            "total_tokens": total_tokens,
            "average_cost_per_operation": float(total_cost / max(total_operations, 1)),
            "average_tokens_per_operation": total_tokens / max(total_operations, 1),
            "most_expensive_agent": {
                "name": most_expensive[0],
                "cost": float(most_expensive[1]["total_cost"])
            } if most_expensive[0] else None,
            "most_active_agent": {
                "name": most_active[0],
                "operations": most_active[1]["operations_count"]
            } if most_active[0] else None,
            "agents": {
                name: {
                    "operations": stats["operations_count"],
                    "total_cost": float(stats["total_cost"]),
                    "total_tokens": stats["total_input_tokens"] + stats["total_output_tokens"],
                    "models_used": list(stats["models_used"]),
                    "operation_types": list(stats["operation_types"].keys())
                }
                for name, stats in self.agent_usage_stats.items()
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get token counter statistics."""
        base_stats = {
            "enabled": self.enabled,
            "total_counts_performed": self.stats["total_counts_performed"],
            "total_tokens_counted": self.stats["total_tokens_counted"],
            "total_cost_calculated": float(self.stats["total_cost_calculated"]),
            "unique_models_processed": len(self.stats["models_processed"]),
            "average_tokens_per_request": self.stats["average_tokens_per_request"],
            "supported_models": len(self.get_supported_models()),
            "estimators_available": len(self.token_estimators)
        }
        
        # Add agent usage stats if available
        if hasattr(self, 'agent_usage_stats') and self.agent_usage_stats:
            base_stats["agent_usage_summary"] = self.get_agent_usage_summary()
        
        return base_stats
    
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
