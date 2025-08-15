"""
Content generation for synthetic data
"""

import random
import uuid
import numpy as np
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any


def select_workload_type() -> str:
    """Select workload type based on distribution"""
    distribution = {
        "simple_queries": 0.30,
        "tool_orchestration": 0.25,
        "data_analysis": 0.20,
        "optimization_workflows": 0.15,
        "error_scenarios": 0.10
    }
    
    types = list(distribution.keys())
    weights = list(distribution.values())
    return np.random.choice(types, p=weights)


def generate_timestamp(config: Any, index: int) -> datetime:
    """Generate realistic timestamp with patterns"""
    base_time = datetime.now(UTC) - timedelta(hours=24)
    
    # Add some variation with business hours pattern
    hour_offset = (index / config.num_logs) * 24
    timestamp = base_time + timedelta(hours=hour_offset)
    
    # Add jitter
    jitter_seconds = random.uniform(-60, 60)
    timestamp += timedelta(seconds=jitter_seconds)
    
    return timestamp


def select_agent_type(workload_type: str) -> str:
    """Select appropriate agent type for workload"""
    agent_mapping = {
        "simple_queries": "triage",
        "tool_orchestration": "supervisor",
        "data_analysis": "data_analysis",
        "optimization_workflows": "optimization",
        "error_scenarios": "triage"
    }
    return agent_mapping.get(workload_type, "general")


def generate_content(
    workload_type: str,
    corpus_content: Optional[List[Dict]]
) -> tuple[str, str]:
    """Generate request/response content"""
    if corpus_content:  # Always use corpus when available
        entry = random.choice(corpus_content)
        return entry.get("prompt", ""), entry.get("response", "")
    
    # Generate synthetic content based on workload type
    content_map = {
        "simple_queries": (
            [
                "What is the weather today?",
                "How do I reset my password?",
                "What are your business hours?",
                "Can you help me with my order?"
            ],
            [
                "I can help you with that information.",
                "Here's what you need to know.",
                "Let me look that up for you.",
                "I've found the answer to your question."
            ]
        ),
        "tool_orchestration": (
            [
                "Analyze my system performance and provide recommendations",
                "Generate a report on last week's metrics",
                "Optimize my database queries",
                "Debug this application issue"
            ],
            [
                "I've completed the analysis with multiple tools.",
                "Report generated successfully after data processing.",
                "Optimization complete with significant improvements.",
                "Issue identified and resolved using diagnostic tools."
            ]
        ),
        "data_analysis": (
            [
                "What are the trends in our data?",
                "Analyze the performance metrics",
                "Generate insights from the logs",
                "Compare this week to last week"
            ],
            [
                "Analysis shows significant patterns in the data.",
                "Performance metrics indicate positive trends.",
                "Key insights have been extracted from the logs.",
                "Comparison reveals notable improvements."
            ]
        )
    }
    
    prompts, responses = content_map.get(workload_type, (["Generic request"], ["Generic response"]))
    return random.choice(prompts), random.choice(responses)


def generate_child_spans(spans: List[Dict], parent: Dict, max_depth: int, max_branches: int, current_depth: int):
    """Recursively generate child spans"""
    if current_depth >= max_depth:
        return
    
    num_children = random.randint(0, max_branches)
    for _ in range(num_children):
        child_span = {
            'span_id': str(uuid.uuid4()),
            'parent_span_id': parent['span_id'],
            'trace_id': parent['trace_id'],
            'start_time': parent['start_time'] + timedelta(milliseconds=random.randint(1, 100)),
            'end_time': None,
            'depth': current_depth
        }
        spans.append(child_span)
        
        # Recursively generate children
        generate_child_spans(spans, child_span, max_depth, max_branches, current_depth + 1)