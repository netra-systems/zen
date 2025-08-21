# Multi-Turn Trace Generation Module for Synthetic Data
# Handles complex conversation trace generation with tool usage

import hashlib
import random
import uuid
from typing import Any, Dict, List

from faker import Faker

from netra_backend.app.log_formatter import (
    _generate_contextual_response,
    format_log_entry,
)

fake = Faker()


def _create_log_data_for_turn(app_config: Dict[str, Any], model_config: Dict[str, Any], prompt: str, response: str) -> Dict[str, Any]:
    """Creates log data dictionary for a single conversation turn."""
    base_data = _create_base_turn_data(app_config, model_config)
    return base_data


def _create_base_turn_data(app_config: Dict[str, Any], model_config: Dict[str, Any]) -> Dict[str, Any]:
    """Creates base log data with app and model information."""
    user_data = _create_user_data()
    app_data = _create_app_data(app_config)
    model_data = _create_model_data(model_config)
    return {**user_data, **app_data, **model_data}


def _create_user_data() -> Dict[str, str]:
    """Creates user identification data."""
    return {
        'user_id': str(uuid.uuid4()),
        'organization_id': f"org_{hashlib.sha256(fake.company().encode()).hexdigest()[:12]}"
    }


def _create_app_data(app_config: Dict[str, Any]) -> Dict[str, str]:
    """Creates application data from config."""
    return {
        'app_name': app_config['app_name'],
        'service_name': random.choice(app_config['services'])
    }


def _create_model_data(model_config: Dict[str, Any]) -> Dict[str, Any]:
    """Creates model data from config."""
    return {
        'model_provider': model_config['provider'],
        'model_name': model_config['name'],
        'model_pricing': model_config['pricing']
    }


def _add_content_and_metrics(log_data: Dict[str, Any], prompt: str, response: str) -> None:
    """Adds content and calculated metrics to log data."""
    _add_content_data(log_data, prompt, response)
    _add_timing_metrics(log_data)


def _add_content_data(log_data: Dict[str, Any], prompt: str, response: str) -> None:
    """Adds content and token information to log data."""
    log_data.update({
        'user_prompt': prompt,
        'assistant_response': response,
        'prompt_tokens': len(prompt.split()) * 2,
        'completion_tokens': len(response.split()) * 2
    })


def _add_timing_metrics(log_data: Dict[str, Any]) -> None:
    """Adds timing metrics to log data."""
    log_data.update({
        'total_e2e_ms': random.randint(300, 2500),
        'ttft_ms': random.randint(150, 900)
    })


def _calculate_costs(log_data: Dict[str, Any]) -> None:
    """Calculates token counts and costs for log data."""
    log_data['total_tokens'] = log_data['prompt_tokens'] + log_data['completion_tokens']
    log_data['prompt_cost'] = (log_data['prompt_tokens'] / 1_000_000) * log_data['model_pricing'][0]
    log_data['completion_cost'] = (log_data['completion_tokens'] / 1_000_000) * log_data['model_pricing'][1]
    log_data['total_cost'] = log_data['prompt_cost'] + log_data['completion_cost']


def _create_trace_context(trace_id: str, span_id: str, parent_span_id: str, turn_index: int) -> Dict[str, Any]:
    """Creates trace context for a conversation turn."""
    base_context = _create_base_trace_context(trace_id, span_id, parent_span_id)
    turn_context = _create_turn_context(turn_index)
    return {**base_context, **turn_context}


def _create_base_trace_context(trace_id: str, span_id: str, parent_span_id: str) -> Dict[str, str]:
    """Creates base trace context information."""
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id
    }


def _create_turn_context(turn_index: int) -> Dict[str, str]:
    """Creates turn-specific context information."""
    return {
        "span_name": f"AgentTurn-{turn_index+1}",
        "span_kind": _get_span_kind(turn_index)
    }


def _get_span_kind(turn_index: int) -> str:
    """Determines span kind based on turn index."""
    return "tool" if turn_index % 2 != 0 else "llm"


def generate_multi_turn_tool_trace(config: Dict[str, Any], content_corpus: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generates a single, complex multi-turn trace with a shared trace_id."""
    conversation = content_corpus.get('multi_turn_tool_use')
    if not conversation:
        return []
    
    trace_setup = _initialize_trace_generation(config)
    return _generate_conversation_logs(trace_setup, conversation)


def _initialize_trace_generation(config: Dict[str, Any]) -> Dict[str, Any]:
    """Initializes trace generation with required configurations."""
    return {
        'trace_id': str(uuid.uuid4()),
        'app_config': random.choice(config['realism']['applications']),
        'model_config': random.choice(config['realism']['models']),
        'parent_span_id': None
    }


def _generate_conversation_logs(trace_setup: Dict[str, Any], conversation: List[Any]) -> List[Dict[str, Any]]:
    """Generates log entries for each turn in the conversation."""
    selected_conversation = random.choice(conversation)
    return _process_all_conversation_turns(trace_setup, selected_conversation)


def _process_all_conversation_turns(trace_setup: Dict[str, Any], selected_conversation: List[Any]) -> List[Dict[str, Any]]:
    """Processes all turns in the selected conversation."""
    trace_logs = []
    parent_span_id = _process_conversation_sequence(trace_setup, selected_conversation, trace_logs)
    return trace_logs


def _process_conversation_sequence(trace_setup: Dict[str, Any], selected_conversation: List[Any], trace_logs: List[Dict[str, Any]]) -> str:
    """Processes the complete conversation sequence."""
    parent_span_id = None
    
    for i, (prompt, response) in enumerate(selected_conversation):
        parent_span_id = _add_conversation_turn(trace_setup, prompt, response, parent_span_id, i, trace_logs)
        
    return parent_span_id


def _add_conversation_turn(trace_setup: Dict[str, Any], prompt: str, response: str, parent_span_id: str, turn_index: int, trace_logs: List[Dict[str, Any]]) -> str:
    """Adds a single conversation turn to the trace logs and returns new parent span ID."""
    log_entry, new_parent_span_id = _process_conversation_turn(trace_setup, prompt, response, parent_span_id, turn_index)
    trace_logs.append(log_entry)
    return new_parent_span_id


def _process_conversation_turn(trace_setup: Dict[str, Any], prompt: str, response: str, parent_span_id: str, turn_index: int) -> tuple[Dict[str, Any], str]:
    """Processes a single conversation turn and returns log entry with updated parent span."""
    log_entry = _create_single_turn_log(trace_setup, prompt, response, parent_span_id, turn_index)
    new_parent_span_id = log_entry['trace_context']['span_id']
    return log_entry, new_parent_span_id


def _create_single_turn_log(trace_setup: Dict[str, Any], prompt: str, response: str, parent_span_id: str, turn_index: int) -> Dict[str, Any]:
    """Creates a single turn log entry."""
    span_id = str(uuid.uuid4())
    log_data = _prepare_turn_log_data(trace_setup, prompt, response)
    trace_context = _create_trace_context(trace_setup['trace_id'], span_id, parent_span_id, turn_index)
    return format_log_entry(log_data, trace_context_override=trace_context)


def _prepare_turn_log_data(trace_setup: Dict[str, Any], prompt: str, response: str) -> Dict[str, Any]:
    """Prepares complete log data for a conversation turn."""
    log_data = _create_log_data_for_turn(trace_setup['app_config'], trace_setup['model_config'], prompt, response)
    _add_content_and_metrics(log_data, prompt, response)
    _calculate_costs(log_data)
    return log_data