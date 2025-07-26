# A Complete Synthetic Data Generation System for the Unified LLM Operations Schema v3.0
#
# This script generates realistic, multi-step LLM operation traces based on the detailed
# schema provided in "Unified LLM Log Structure v3.0". It is designed to be flexible,
# allowing for customer-specific overrides to make the data relevant to any environment.
#
# Key Features:
# 1.  Schema-Compliant: Uses Pydantic to strictly enforce the v3.0 schema.
# 2.  Realistic Traces: Generates multi-span traces for common workflows (RAG, Tool Use, etc.).
# 3.  AI-Powered Realism: Uses the Gemini Flash model to generate plausible prompts and responses.
# 4.  Highly Flexible: Configuration is managed via a YAML file, allowing easy customization.
# 5.  Customer Overrides: Allows users to override any field in the log to match their specific setup.
#
# SETUP:
# 1. Install necessary libraries:
#    pip install pydantic faker pyyaml rich
#
# 2. (Optional but Recommended) For AI-powered content generation:
#    pip install google-generativeai
#    export GEMINI_API_KEY="YOUR_API_KEY"
#
# USAGE:
# 1. A default `config.yaml` will be created on first run. Customize it as needed.
# 2. Run the script from your terminal:
#    python main.py --num-traces 10 --output-file generated_logs.json
#
# 3. The output will be a JSON file containing a list of generated traces.

import json
import random
import uuid
import time
import datetime
import hashlib
import os
import sys
from typing import List, Optional, Dict, Any, Literal

import yaml
from faker import Faker
from pydantic import BaseModel, Field, HttpUrl
from rich.console import Console
from rich.progress import Progress
from dotenv import load_dotenv

load_dotenv()

# --- Gemini Integration for Realistic Content ---
try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
except ImportError:
    genai = None

console = Console()
fake = Faker()

# --- 1. SCHEMA DEFINITION (Pydantic Models based on v3.0 Spec) ---
# This section meticulously translates the Unified LLM Log Structure v3.0
# into Pydantic models. This ensures all generated data is valid and schema-compliant.

class EventMetadata(BaseModel):
    log_schema_version: str = "3.0.0"
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_utc: int = Field(default_factory=lambda: int(time.time() * 1000))
    ingestion_source: str

class TraceContext(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    span_name: str
    span_kind: Literal["llm", "agent", "workflow", "tool", "task", "embedding", "retrieval"]

class IdentityContext(BaseModel):
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    api_key_hash: Optional[str] = None
    auth_method: Optional[Literal["api_key", "jwt", "iam_role", "oauth"]] = None

class ApplicationContext(BaseModel):
    app_name: str
    service_name: str
    sdk_version: str
    environment: Literal["production", "staging", "development", "test"]
    client_ip: Optional[str] = None

class ModelInfo(BaseModel):
    provider: str
    family: str
    name: str
    version_id: Optional[str] = None

class MultimodalPart(BaseModel):
    part_type: Literal["image", "audio", "video", "file"]
    mime_type: str
    source_uri: Optional[HttpUrl] = None
    source_base64_hash: Optional[str] = None

class PromptMessage(BaseModel):
    role: Literal["user", "assistant", "tool", "system"]
    content: Any # Can be string or list of multimodal parts

class Prompt(BaseModel):
    messages: List[PromptMessage]
    system_prompt: Optional[str] = None
    multimodal_parts: Optional[List[MultimodalPart]] = None

class GenerationConfig(BaseModel):
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_tokens_to_sample: int
    stop_sequences: Optional[List[str]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    seed: Optional[int] = None
    is_streaming: bool

class ToolConfig(BaseModel):
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None # string or object
    allow_parallel_tool_calls: Optional[bool] = None

class StructuredOutputConfig(BaseModel):
    response_format_type: Optional[Literal["json_object", "json_schema"]] = None
    json_schema: Optional[Dict[str, Any]] = None

class CachingConfig(BaseModel):
    use_cache: bool
    cache_type: Optional[Literal["simple", "semantic"]] = None
    force_refresh: bool

class AdvancedFeatures(BaseModel):
    tool_config: Optional[ToolConfig] = None
    structured_output_config: Optional[StructuredOutputConfig] = None
    caching_config: Optional[CachingConfig] = None
    provider_specific_config: Optional[Dict[str, Any]] = None

class Request(BaseModel):
    model: ModelInfo
    prompt: Prompt
    generation_config: GenerationConfig
    advanced_features: Optional[AdvancedFeatures] = None

class CompletionChoice(BaseModel):
    index: int
    finish_reason: Literal["stop_sequence", "max_tokens", "tool_calls", "safety", "recitation", "error", "unknown"]
    message: PromptMessage
    logprobs: Optional[Dict[str, Any]] = None

class Completion(BaseModel):
    choices: List[CompletionChoice]

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    tool_call_tokens: Optional[int] = None
    cached_input_tokens: Optional[int] = None

class RateLimitInfo(BaseModel):
    limit_requests: int
    limit_tokens: int
    remaining_requests: int
    remaining_tokens: int
    reset_requests_at_utc: int
    reset_tokens_at_utc: int

class SystemInfo(BaseModel):
    provider_request_id: str
    system_fingerprint: Optional[str] = None
    provider_processing_ms: Optional[int] = None
    rate_limit_info: Optional[RateLimitInfo] = None

class ToolCallFunction(BaseModel):
    name: str
    arguments: str # JSON string

class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: ToolCallFunction

class Response(BaseModel):
    completion: Completion
    usage: Usage
    system: SystemInfo
    tool_calls: Optional[List[ToolCall]] = None

class Latency(BaseModel):
    total_e2e: int
    time_to_first_token: Optional[int] = None
    time_per_output_token: Optional[float] = None
    queue_duration: Optional[int] = None
    prefill_duration: Optional[int] = None
    decode_duration: Optional[int] = None

class SelfHostedScheduler(BaseModel):
    running_requests: int
    waiting_requests: int
    swapped_requests: int
    preemptions_total: int

class SelfHostedKVCache(BaseModel):
    gpu_usage_percent: float
    cpu_usage_percent: float

class SelfHostedBatchInfo(BaseModel):
    batch_size_current: int
    batch_tokens_current: int

class SelfHostedSpeculativeDecoding(BaseModel):
    draft_tokens: int
    accepted_tokens: int
    efficiency_rate: float

class SelfHostedHardware(BaseModel):
    accelerator_type: str
    accelerator_count: int
    quantization_type: Optional[str] = None

class SelfHostedMetrics(BaseModel):
    server_type: Literal["vllm", "tgi", "ollama", "tensorrt-llm"]
    scheduler: SelfHostedScheduler
    kv_cache: SelfHostedKVCache
    batch_info: SelfHostedBatchInfo
    speculative_decoding: Optional[SelfHostedSpeculativeDecoding] = None
    hardware_info: SelfHostedHardware

class Performance(BaseModel):
    latency_ms: Latency
    self_hosted_metrics: Optional[SelfHostedMetrics] = None

class Cost(BaseModel):
    total_cost_usd: float
    prompt_cost_usd: float
    completion_cost_usd: float
    tool_use_cost_usd: Optional[float] = None

class PricingInfo(BaseModel):
    provider_rate_id: str
    prompt_token_rate_usd_per_million: float
    completion_token_rate_usd_per_million: float
    cached_token_rate_usd_per_million: Optional[float] = None

class Attribution(BaseModel):
    cost_center_id: Optional[str] = None
    project_id: Optional[str] = None
    team_id: Optional[str] = None
    feature_name: Optional[str] = None

class BudgetContext(BaseModel):
    budget_id: str
    budget_consumption_usd: float
    budget_limit_usd: float
    budget_alert_triggered: bool

class FinOps(BaseModel):
    cost: Cost
    pricing_info: PricingInfo
    attribution: Optional[Attribution] = None
    budget_context: Optional[BudgetContext] = None

class Security(BaseModel):
    pii_redacted: bool
    detected_pii_types: Optional[List[str]] = None
    prompt_injection_detected: bool
    prompt_injection_score: Optional[float] = None

class ProviderSafetyRating(BaseModel):
    category: Literal["hate_speech", "harassment", "sexual_content", "dangerous_content"]
    severity: Literal["negligible", "low", "medium", "high"]
    was_blocked: bool

class Safety(BaseModel):
    provider_safety_ratings: List[ProviderSafetyRating]
    overall_safety_verdict: Literal["pass", "fail", "flagged"]

class UserFeedback(BaseModel):
    score: float
    comment: Optional[str] = None

class RagEvaluations(BaseModel):
    contextual_precision: float
    contextual_recall: float
    faithfulness: float
    answer_relevancy: float

class Quality(BaseModel):
    is_hallucination: Optional[bool] = None
    is_refusal: Optional[bool] = None
    user_feedback: Optional[UserFeedback] = None
    rag_evaluations: Optional[RagEvaluations] = None

class AuditContext(BaseModel):
    request_type: Literal["initial", "retry", "fallback"]
    initial_request_id: Optional[str] = None
    cache_status: Literal["hit", "miss", "disabled", "refresh"]

class Governance(BaseModel):
    security: Security
    safety: Safety
    quality: Optional[Quality] = None
    audit_context: AuditContext

class WorkloadProfile(BaseModel):
    profile_id: str
    profile_name: str
    profile_description: str
    confidence_score: float

class OptimizationRecommendation(BaseModel):
    recommended_model: ModelInfo
    predicted_cost_usd: float
    predicted_latency_ms: Dict[str, Any]
    predicted_quality_score: float
    savings_potential_usd: float

class OptimizationContext(BaseModel):
    utility_function_id: str
    utility_score_calculated: float
    optimization_recommendation: Optional[OptimizationRecommendation] = None

class EnrichedAnalytics(BaseModel):
    workload_profile: WorkloadProfile
    optimization_context: OptimizationContext

class UnifiedLogEntry(BaseModel):
    event_metadata: EventMetadata
    trace_context: TraceContext
    identity_context: Optional[IdentityContext] = None
    application_context: ApplicationContext
    request: Request
    response: Optional[Response] = None
    performance: Performance
    finops: Optional[FinOps] = None
    governance: Optional[Governance] = None
    enriched_analytics: Optional[EnrichedAnalytics] = None

# --- 2. CONFIGURATION MANAGEMENT ---
DEFAULT_CONFIG = """
# Configuration for the Synthetic Log Generator
# This file controls the behavior of the data generation process.

# --- General Settings ---
generation_settings:
  # Default number of traces to generate if not specified via command line.
  num_traces: 5
  # The distribution of different trace types to generate. Values should sum to 1.0.
  trace_distribution:
    simple_chat: 0.4
    rag_pipeline: 0.3
    tool_use: 0.2
    failed_request: 0.1

# --- Realism Engine Settings ---
# These settings control the data generated for various fields.
realism:
  # List of possible applications and services to simulate.
  applications:
    - app_name: "customer-support-chatbot"
      services: ["intent-classifier", "chat-responder", "history-summarizer"]
    - app_name: "marketing-copy-generator"
      services: ["headline-generator", "body-text-creator", "seo-analyzer"]
    - app_name: "internal-doc-search"
      services: ["query-parser", "retrieval-engine", "answer-generator"]
  
  # List of possible model providers and their models.
  # Pricing is in USD per 1 Million tokens (prompt, completion).
  models:
    - provider: "openai"
      family: "gpt-4"
      name: "gpt-4o"
      version_id: "gpt-4o-2024-08-06"
      pricing: [5.00, 15.00]
    - provider: "anthropic"
      family: "claude-3"
      name: "claude-3-opus"
      version_id: "claude-3-opus-20240229"
      pricing: [15.00, 75.00]
    - provider: "google"
      family: "gemini-2.0"
      name: "gemini-2.0-flash"
      version_id: null
      pricing: [0.35, 0.70]
    - provider: "vllm"
      family: "llama-3.1"
      name: "llama-3.1-70b-instruct"
      version_id: null
      pricing: [0.50, 0.50] # Example self-hosted cost

# --- Customer Overrides ---
# Use this section to force specific values for any field in the log schema.
# This is powerful for tailoring the data to a specific customer's environment.
# The keys should match the structure of the UnifiedLogEntry schema.
# Example:
# overrides:
#   identity_context:
#     organization_id: "acme-corp-xyz"
#   application_context:
#     environment: "production"
#   finops:
#     attribution:
#       cost_center_id: "R&D-AI-Division"

overrides: {}
"""

def get_config(config_path="config.yaml"):
    """Loads configuration from a YAML file."""
    if not os.path.exists(config_path):
        console.print(f"[yellow]Config file not found. Creating default '{config_path}'...[/yellow]")
        with open(config_path, "w") as f:
            f.write(DEFAULT_CONFIG)
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

# --- 3. REALISM ENGINE ---
# This module is responsible for generating realistic values for individual fields.

class RealismEngine:
    def __init__(self, config):
        self.config = config
        self.gemini_model = None
        if genai and GEMINI_API_KEY:
            try:
                self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
                console.print("[green]Gemini Flash model initialized for content generation.[/green]")
            except Exception as e:
                console.print(f"[red]Failed to initialize Gemini model: {e}[/red]")
                self.gemini_model = None

    def _get_random_model(self):
        return random.choice(self.config['realism']['models'])

    def _hash_value(self, value):
        return hashlib.sha256(value.encode()).hexdigest()

    def generate_content_with_gemini(self, workload_type: str) -> Dict[str, Any]:
        """Generates a realistic prompt and completion using Gemini."""
        if not self.gemini_model:
            return {
                "user_prompt": f"This is a dummy prompt for workload: {workload_type}.",
                "assistant_response": "This is a dummy response as Gemini is not configured."
            }
        
        system_prompts = {
            "chat": "You are a helpful assistant.",
            "summarization": "Summarize the following text.",
            "rag": "Based on the provided context, answer the user's question.",
            "tool_use": "You have access to tools. Use them if necessary to answer the user.",
            "code": "You are a coding assistant. Provide code snippets as requested."
        }
        
        user_prompts = {
            "chat": "What are the main benefits of using a unified logging schema for LLM operations?",
            "summarization": "The enterprise adoption of Large Language Models (LLMs) is occurring in a period of rapid, chaotic expansion...",
            "rag": "Context: The v3.0 schema is designed to be the most comprehensive data model for LLM operations. Question: What is the main design goal of the v3.0 schema?",
            "tool_use": "What's the weather like in San Francisco and what is 5*128?",
            "code": "Write a python function to calculate the factorial of a number."
        }

        try:
            prompt_text = f"""
            Based on the workload type '{workload_type}', generate a realistic user prompt and a corresponding assistant response.
            
            System Prompt: {system_prompts.get(workload_type, "You are a helpful assistant.")}
            Example User Prompt: {user_prompts.get(workload_type, "Tell me something interesting.")}

            Return ONLY a JSON object with two keys: "user_prompt" and "assistant_response".
            """
            response = self.gemini_model.generate_content(prompt_text)
            
            # Clean the response text to extract the JSON part
            cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
            content = json.loads(cleaned_text)
            return content

        except Exception as e:
            console.print(f"[red]Error during Gemini content generation: {e}[/red]")
            return {
                "user_prompt": f"Error generating prompt for {workload_type}.",
                "assistant_response": f"Error generating response: {e}"
            }

    def generate_model_info(self):
        model_data = self._get_random_model()
        return ModelInfo(**{k: v for k, v in model_data.items() if k != 'pricing'}), model_data['pricing']

    def generate_application_context(self):
        app_config = random.choice(self.config['realism']['applications'])
        return ApplicationContext(
            app_name=app_config['app_name'],
            service_name=random.choice(app_config['services']),
            sdk_version=f"python-sdk-{random.randint(1,3)}.{random.randint(0,10)}.{random.randint(0,5)}",
            environment=random.choice(["production", "staging", "development"]),
            client_ip=fake.ipv4()
        )

    def generate_identity_context(self):
        return IdentityContext(
            user_id=str(uuid.uuid4()),
            organization_id=f"org_{self._hash_value(fake.company())[:12]}",
            api_key_hash=self._hash_value(str(uuid.uuid4())),
            auth_method=random.choice(["api_key", "jwt", "iam_role"])
        )

    def generate_finops(self, usage: Usage, pricing: List[float]):
        prompt_cost = (usage.prompt_tokens / 1_000_000) * pricing[0]
        completion_cost = (usage.completion_tokens / 1_000_000) * pricing[1]
        total_cost = prompt_cost + completion_cost
        
        return FinOps(
            cost=Cost(
                total_cost_usd=total_cost,
                prompt_cost_usd=prompt_cost,
                completion_cost_usd=completion_cost
            ),
            pricing_info=PricingInfo(
                provider_rate_id=f"rate_{str(uuid.uuid4())[:8]}",
                prompt_token_rate_usd_per_million=pricing[0],
                completion_token_rate_usd_per_million=pricing[1]
            ),
            attribution=Attribution(
                cost_center_id=f"CC_{random.randint(100, 999)}",
                project_id=f"PROJ_{str(uuid.uuid4())[:6].upper()}",
                team_id=random.choice(["alpha", "beta", "gamma"]),
                feature_name=random.choice(["summarization", "chat", "search"])
            )
        )

    def generate_governance(self, request_type="initial", cache_status="miss"):
        return Governance(
            security=Security(
                pii_redacted=random.random() < 0.1,
                prompt_injection_detected=random.random() < 0.05,
                prompt_injection_score=random.random() if random.random() < 0.05 else None
            ),
            safety=Safety(
                provider_safety_ratings=[
                    ProviderSafetyRating(
                        category=cat,
                        severity=random.choice(["negligible", "low"]),
                        was_blocked=False
                    ) for cat in ["hate_speech", "harassment", "sexual_content", "dangerous_content"]
                ],
                overall_safety_verdict="pass"
            ),
            audit_context=AuditContext(
                request_type=request_type,
                cache_status=cache_status
            )
        )

# --- 4. TRACE & LOG GENERATION ---
class LogGenerator:
    """Generates a single, complete UnifiedLogEntry."""
    def __init__(self, realism_engine: RealismEngine):
        self.realism = realism_engine

    def generate(self, trace_context: TraceContext, overrides: Dict = None, **kwargs) -> Dict:
        # Generate base components
        model_info, pricing = self.realism.generate_model_info()
        app_context = self.realism.generate_application_context()
        identity_context = self.realism.generate_identity_context()

        # Generate content
        workload_type = kwargs.get("workload_type", "chat")
        content = self.realism.generate_content_with_gemini(workload_type)
        user_prompt = content['user_prompt']
        assistant_response = content['assistant_response']

        # Generate usage and timing
        prompt_tokens = len(user_prompt.split()) * 2
        completion_tokens = len(assistant_response.split()) * 2
        total_tokens = prompt_tokens + completion_tokens
        
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens
        )
        
        ttft = random.randint(150, 800)
        tpot = random.uniform(10.5, 50.5)
        decode_duration = int(completion_tokens * tpot)
        total_e2e = ttft + decode_duration + random.randint(50, 150) # network latency
        
        latency = Latency(total_e2e=total_e2e, time_to_first_token=ttft, time_per_output_token=tpot, decode_duration=decode_duration)
        
        # Assemble the log entry
        log_entry = UnifiedLogEntry(
            event_metadata=EventMetadata(ingestion_source="synthetic_generator_v1"),
            trace_context=trace_context,
            identity_context=identity_context,
            application_context=app_context,
            request=Request(
                model=model_info,
                prompt=Prompt(messages=[PromptMessage(role="user", content=user_prompt)]),
                generation_config=GenerationConfig(max_tokens_to_sample=2048, is_streaming=False, temperature=0.7)
            ),
            response=Response(
                completion=Completion(choices=[
                    CompletionChoice(index=0, finish_reason="stop_sequence", message=PromptMessage(role="assistant", content=assistant_response))
                ]),
                usage=usage,
                system=SystemInfo(provider_request_id=f"req_{str(uuid.uuid4())}")
            ),
            performance=Performance(latency_ms=latency),
            finops=self.realism.generate_finops(usage, pricing),
            governance=self.realism.generate_governance()
        )
        
        # Convert to dict and apply overrides
        log_dict = log_entry.dict(exclude_none=True)
        if overrides:
            log_dict = self._deep_merge(log_dict, overrides)
        
        return log_dict

    def _deep_merge(self, source, destination):
        """Recursively merge dictionaries."""
        for key, value in destination.items():
            if isinstance(value, dict):
                node = source.setdefault(key, {})
                self._deep_merge(node, value)
            else:
                source[key] = value
        return source

class TraceGenerator:
    """Generates a complete trace, which is a list of log entries."""
    def __init__(self, log_generator: LogGenerator, overrides: Dict):
        self.log_generator = log_generator
        self.overrides = overrides

    def generate_trace(self, trace_type: str) -> List[Dict]:
        trace_id = str(uuid.uuid4())
        
        if trace_type == "simple_chat":
            return self._generate_simple_chat(trace_id)
        elif trace_type == "rag_pipeline":
            return self._generate_rag_pipeline(trace_id)
        elif trace_type == "tool_use":
            return self._generate_tool_use(trace_id)
        elif trace_type == "failed_request":
            return self._generate_failed_request(trace_id)
        else:
            return self._generate_simple_chat(trace_id)

    def _generate_simple_chat(self, trace_id):
        span_id = str(uuid.uuid4())
        trace_context = TraceContext(trace_id=trace_id, span_id=span_id, span_name="UserChat", span_kind="llm")
        log = self.log_generator.generate(trace_context, self.overrides, workload_type="chat")
        return [log]

    def _generate_rag_pipeline(self, trace_id):
        # 1. Workflow Span (Root)
        workflow_span_id = str(uuid.uuid4())
        workflow_context = TraceContext(trace_id=trace_id, span_id=workflow_span_id, span_name="RAGWorkflow", span_kind="workflow")
        # A workflow span might not have a full request/response, just metadata and timing.
        # For simplicity, we'll generate a full log but could be trimmed down.
        workflow_log = self.log_generator.generate(workflow_context, self.overrides, workload_type="rag")
        
        # 2. Retrieval Span
        retrieval_span_id = str(uuid.uuid4())
        retrieval_context = TraceContext(trace_id=trace_id, span_id=retrieval_span_id, parent_span_id=workflow_span_id, span_name="VectorDBSearch", span_kind="retrieval")
        retrieval_log = self.log_generator.generate(retrieval_context, self.overrides, workload_type="rag")
        # Modify to look more like a retrieval task
        retrieval_log['request']['prompt']['messages'] = [{"role": "system", "content": "Retrieving documents for query."}]
        retrieval_log['response'] = None # No LLM response for retrieval
        retrieval_log['performance']['latency_ms']['total_e2e'] = random.randint(50, 200)

        # 3. LLM Call Span
        llm_span_id = str(uuid.uuid4())
        llm_context = TraceContext(trace_id=trace_id, span_id=llm_span_id, parent_span_id=workflow_span_id, span_name="GenerateFinalAnswer", span_kind="llm")
        llm_log = self.log_generator.generate(llm_context, self.overrides, workload_type="rag")
        
        return [workflow_log, retrieval_log, llm_log]

    def _generate_tool_use(self, trace_id):
        span_id = str(uuid.uuid4())
        trace_context = TraceContext(trace_id=trace_id, span_id=span_id, span_name="FunctionCalling", span_kind="llm")
        log = self.log_generator.generate(trace_context, self.overrides, workload_type="tool_use")
        
        # Add tool use data
        tool_call_id = f"call_{str(uuid.uuid4())[:8]}"
        log['response']['completion']['choices'][0]['finish_reason'] = 'tool_calls'
        log['response']['tool_calls'] = [
            ToolCall(
                id=tool_call_id,
                function=ToolCallFunction(
                    name="get_weather",
                    arguments=json.dumps({"location": "San Francisco, CA"})
                )
            ).dict()
        ]
        return [log]

    def _generate_failed_request(self, trace_id):
        # 1. Initial Failed Request
        initial_span_id = str(uuid.uuid4())
        initial_context = TraceContext(trace_id=trace_id, span_id=initial_span_id, span_name="PrimaryModelCall", span_kind="llm")
        initial_log = self.log_generator.generate(initial_context, self.overrides, workload_type="chat")
        initial_log['response'] = None # It failed
        initial_log['governance']['audit_context']['request_type'] = 'initial'
        
        # 2. Fallback Successful Request
        fallback_span_id = str(uuid.uuid4())
        fallback_context = TraceContext(trace_id=trace_id, span_id=fallback_span_id, parent_span_id=initial_span_id, span_name="FallbackModelCall", span_kind="llm")
        fallback_log = self.log_generator.generate(fallback_context, self.overrides, workload_type="chat")
        fallback_log['governance']['audit_context']['request_type'] = 'fallback'
        fallback_log['governance']['audit_context']['initial_request_id'] = initial_span_id
        
        return [initial_log, fallback_log]

# --- 5. ORCHESTRATION ---
def main(args):
    """Main function to run the generator."""
    console.print("[bold cyan]Starting Synthetic Log Generation...[/bold cyan]")
    
    config = get_config(args.config)
    
    realism_engine = RealismEngine(config)
    log_generator = LogGenerator(realism_engine)
    trace_generator = TraceGenerator(log_generator, config.get('overrides', {}))
    
    trace_distribution = config['generation_settings']['trace_distribution']
    trace_types = list(trace_distribution.keys())
    weights = list(trace_distribution.values())
    
    all_traces = []
    
    with Progress() as progress:
        task = progress.add_task("[green]Generating traces...", total=args.num_traces)
        for _ in range(args.num_traces):
            chosen_trace_type = random.choices(trace_types, weights, k=1)[0]
            trace = trace_generator.generate_trace(chosen_trace_type)
            all_traces.append(trace)
            progress.update(task, advance=1)
            
    # Save to file
    with open(args.output_file, 'w') as f:
        json.dump(all_traces, f, indent=2)
        
    console.print(f"\n[bold green]Successfully generated {args.num_traces} traces.[/bold green]")
    console.print(f"Output saved to [cyan]{args.output_file}[/cyan]")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Synthetic Log Generator for Unified LLM Schema v3.0")
    parser.add_argument("--config", default="config.yaml", help="Path to the configuration YAML file.")
    parser.add_argument("--num-traces", type=int, default=10, help="Number of traces to generate.")
    parser.add_argument("--output-file", default="generated_logs.json", help="Path to the output JSON file.")
    
    # In some environments, sys.argv might be empty.
    if len(sys.argv) == 1:
        # Provide default arguments if none are given
        args = parser.parse_args(['--num-traces', '10', '--output-file', 'generated_logs.json'])
    else:
        args = parser.parse_args()

    main(args)
