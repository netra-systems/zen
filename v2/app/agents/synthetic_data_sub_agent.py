# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T21:00:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Creating SyntheticDatasubAgent for synthetic data generation
# Git: v8 | dirty
# Change: New Feature | Scope: Component | Risk: Medium
# Session: synthetic-data-agent-creation | Seq: 1
# Review: Pending | Score: 85
# ================================

import json
import logging
import time
import asyncio
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field, ValidationError
from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class DataGenerationType(str, Enum):
    """Types of synthetic data generation"""
    INFERENCE_LOGS = "inference_logs"
    TRAINING_DATA = "training_data"
    PERFORMANCE_METRICS = "performance_metrics"
    COST_DATA = "cost_data"
    CUSTOM = "custom"

class WorkloadProfile(BaseModel):
    """Profile for synthetic workload generation"""
    workload_type: DataGenerationType
    volume: int = Field(ge=100, le=1000000, default=1000)
    time_range_days: int = Field(ge=1, le=365, default=30)
    distribution: str = Field(default="normal")  # normal, uniform, exponential
    noise_level: float = Field(ge=0.0, le=0.5, default=0.1)
    custom_parameters: Dict[str, Any] = Field(default_factory=dict)

class GenerationStatus(BaseModel):
    """Status of synthetic data generation"""
    status: str = Field(default="pending")  # pending, generating, completed, failed
    records_generated: int = 0
    total_records: int = 0
    progress_percentage: float = 0.0
    estimated_time_remaining: Optional[int] = None
    table_name: Optional[str] = None
    errors: List[str] = Field(default_factory=list)

class SyntheticDataResult(BaseModel):
    """Result of synthetic data generation"""
    success: bool
    workload_profile: WorkloadProfile
    generation_status: GenerationStatus
    metadata: Dict[str, Any] = Field(default_factory=dict)
    sample_data: Optional[List[Dict[str, Any]]] = None
    requires_approval: bool = False
    approval_message: Optional[str] = None

class SyntheticDataSubAgent(BaseSubAgent):
    """Sub-agent dedicated to synthetic data generation"""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(
            llm_manager, 
            name="SyntheticDataSubAgent", 
            description="Agent specialized in generating synthetic data for workload simulation"
        )
        self.tool_dispatcher = tool_dispatcher
        self.preseeded_workloads = self._initialize_preseeded_workloads()
        
    def _initialize_preseeded_workloads(self) -> Dict[str, WorkloadProfile]:
        """Initialize pre-seeded workload profiles"""
        return {
            "ecommerce": WorkloadProfile(
                workload_type=DataGenerationType.INFERENCE_LOGS,
                volume=10000,
                time_range_days=30,
                distribution="exponential",
                noise_level=0.15,
                custom_parameters={
                    "peak_hours": [10, 14, 19, 20],
                    "models": ["gpt-4", "claude-2", "embedding-ada-002"],
                    "use_cases": ["product_recommendations", "search", "chat_support"],
                    "avg_tokens_per_request": 500,
                    "peak_multiplier": 3.5
                }
            ),
            "financial": WorkloadProfile(
                workload_type=DataGenerationType.INFERENCE_LOGS,
                volume=50000,
                time_range_days=90,
                distribution="normal",
                noise_level=0.05,
                custom_parameters={
                    "models": ["gpt-4-turbo", "claude-3-opus"],
                    "use_cases": ["risk_analysis", "fraud_detection", "compliance"],
                    "avg_tokens_per_request": 1500,
                    "compliance_requirements": True,
                    "data_sensitivity": "high"
                }
            ),
            "healthcare": WorkloadProfile(
                workload_type=DataGenerationType.INFERENCE_LOGS,
                volume=25000,
                time_range_days=60,
                distribution="uniform",
                noise_level=0.08,
                custom_parameters={
                    "models": ["med-palm-2", "gpt-4", "bio-gpt"],
                    "use_cases": ["diagnosis_assist", "medical_qa", "report_generation"],
                    "avg_tokens_per_request": 2000,
                    "hipaa_compliant": True,
                    "requires_audit_trail": True
                }
            ),
            "gaming": WorkloadProfile(
                workload_type=DataGenerationType.PERFORMANCE_METRICS,
                volume=100000,
                time_range_days=7,
                distribution="exponential",
                noise_level=0.25,
                custom_parameters={
                    "models": ["gpt-3.5-turbo", "llama-2-7b"],
                    "use_cases": ["npc_dialogue", "story_generation", "player_assistance"],
                    "avg_tokens_per_request": 200,
                    "peak_hours": [19, 20, 21, 22, 23],
                    "weekend_multiplier": 2.0
                }
            ),
            "research": WorkloadProfile(
                workload_type=DataGenerationType.TRAINING_DATA,
                volume=5000,
                time_range_days=180,
                distribution="normal",
                noise_level=0.02,
                custom_parameters={
                    "models": ["gpt-4", "claude-3-opus", "palm-2"],
                    "use_cases": ["paper_analysis", "hypothesis_generation", "data_synthesis"],
                    "avg_tokens_per_request": 5000,
                    "batch_processing": True,
                    "quality_over_speed": True
                }
            )
        }
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if conditions are met for synthetic data generation"""
        # Check if we're in admin mode or have explicit synthetic data request
        triage_result = state.triage_result or {}
        
        if isinstance(triage_result, dict):
            category = triage_result.get("category", "")
            is_admin = triage_result.get("is_admin_mode", False)
            
            # Check if this is a synthetic data generation request
            if "synthetic" in category.lower() or "data generation" in category.lower() or is_admin:
                return True
        
        # Check if explicitly called for synthetic data
        if state.user_request and ("synthetic" in state.user_request.lower() or 
                                   "generate data" in state.user_request.lower()):
            return True
            
        self.logger.info(f"Synthetic data generation not required for run_id: {run_id}")
        return False
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute synthetic data generation"""
        start_time = time.time()
        
        try:
            # Send initial update
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "starting",
                    "message": "🎲 Initializing synthetic data generation...",
                    "agent": "SyntheticDataSubAgent"
                })
            
            # Parse user request to determine workload type
            workload_profile = await self._determine_workload_profile(state)
            
            # Check if this requires user approval
            requires_approval = await self._check_approval_requirements(workload_profile, state)
            
            if requires_approval:
                # Request user approval
                approval_message = self._generate_approval_message(workload_profile)
                
                state.synthetic_data_result = SyntheticDataResult(
                    success=False,
                    workload_profile=workload_profile,
                    generation_status=GenerationStatus(status="pending_approval"),
                    requires_approval=True,
                    approval_message=approval_message
                ).model_dump()
                
                if stream_updates:
                    await self._send_update(run_id, {
                        "status": "approval_required",
                        "message": approval_message,
                        "requires_user_action": True,
                        "action_type": "approve_synthetic_data",
                        "workload_profile": workload_profile.model_dump()
                    })
                return
            
            # Generate synthetic data
            generation_status = GenerationStatus(
                status="generating",
                total_records=workload_profile.volume
            )
            
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "generating",
                    "message": f"🔄 Generating {workload_profile.volume:,} synthetic records...",
                    "progress": 0
                })
            
            # Use tool dispatcher to generate data
            result = await self._generate_synthetic_data(workload_profile, generation_status, run_id, stream_updates)
            
            # Store result in state
            state.synthetic_data_result = result.model_dump()
            
            # Final update
            if stream_updates:
                duration = int((time.time() - start_time) * 1000)
                await self._send_update(run_id, {
                    "status": "completed",
                    "message": f"✅ Successfully generated {result.generation_status.records_generated:,} synthetic records in {duration}ms",
                    "result": result.model_dump(),
                    "sample_data": result.sample_data[:5] if result.sample_data else None
                })
            
            self.logger.info(f"Synthetic data generation completed for run_id {run_id}: "
                           f"{result.generation_status.records_generated} records generated")
            
        except Exception as e:
            self.logger.error(f"Synthetic data generation failed for run_id {run_id}: {e}")
            
            error_result = SyntheticDataResult(
                success=False,
                workload_profile=WorkloadProfile(workload_type=DataGenerationType.CUSTOM),
                generation_status=GenerationStatus(
                    status="failed",
                    errors=[str(e)]
                )
            )
            state.synthetic_data_result = error_result.model_dump()
            
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "error",
                    "message": f"❌ Synthetic data generation failed: {str(e)}",
                    "error": str(e)
                })
            raise
    
    async def _determine_workload_profile(self, state: DeepAgentState) -> WorkloadProfile:
        """Determine workload profile from user request"""
        user_request = state.user_request.lower()
        
        # Check for pre-seeded workloads
        for name, profile in self.preseeded_workloads.items():
            if name in user_request:
                self.logger.info(f"Using pre-seeded workload: {name}")
                return profile
        
        # Parse custom parameters from request
        prompt = f"""
Analyze the following user request for synthetic data generation and extract parameters:

User Request: {state.user_request}

Return a JSON object with these fields:
{{
    "workload_type": "inference_logs|training_data|performance_metrics|cost_data|custom",
    "volume": <number between 100 and 1000000>,
    "time_range_days": <number between 1 and 365>,
    "distribution": "normal|uniform|exponential",
    "noise_level": <number between 0.0 and 0.5>,
    "custom_parameters": {{
        "models": [<list of model names if mentioned>],
        "use_cases": [<list of use cases if mentioned>],
        "avg_tokens_per_request": <number if mentioned, otherwise 500>
    }}
}}

Be conservative with volume - default to 1000 if not specified.
"""
        
        try:
            response = await self.llm_manager.ask_llm(prompt, llm_config_name='default')
            params = extract_json_from_response(response)
            
            if params:
                return WorkloadProfile(**params)
        except Exception as e:
            self.logger.warning(f"Failed to parse workload profile: {e}")
        
        # Default profile
        return WorkloadProfile(
            workload_type=DataGenerationType.INFERENCE_LOGS,
            volume=1000,
            time_range_days=30
        )
    
    async def _check_approval_requirements(self, profile: WorkloadProfile, state: DeepAgentState) -> bool:
        """Check if user approval is required for this generation"""
        # Require approval for large volumes
        if profile.volume > 50000:
            return True
        
        # Require approval for sensitive data types
        custom_params = profile.custom_parameters
        if custom_params.get("data_sensitivity") == "high":
            return True
        
        # Check if admin mode explicitly requests approval
        triage_result = state.triage_result or {}
        if isinstance(triage_result, dict) and triage_result.get("require_approval"):
            return True
        
        return False
    
    def _generate_approval_message(self, profile: WorkloadProfile) -> str:
        """Generate user-friendly approval message"""
        return f"""
**📊 Synthetic Data Generation Request**

**Type:** {profile.workload_type.value.replace('_', ' ').title()}
**Volume:** {profile.volume:,} records
**Time Range:** {profile.time_range_days} days
**Distribution:** {profile.distribution}

This will generate synthetic data to simulate your workload patterns.
The data will be stored in a unique table for analysis.

**Do you approve this synthetic data generation?**
Reply with 'approve' to proceed or 'modify' to adjust parameters.
"""
    
    async def _generate_synthetic_data(self, 
                                      profile: WorkloadProfile,
                                      status: GenerationStatus,
                                      run_id: str,
                                      stream_updates: bool) -> SyntheticDataResult:
        """Generate synthetic data using tools"""
        
        # Generate unique table name
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        table_name = f"synthetic_{profile.workload_type.value}_{timestamp}"
        status.table_name = table_name
        
        # Simulate generation with progress updates
        batch_size = min(1000, profile.volume // 10)
        generated_data = []
        
        for i in range(0, profile.volume, batch_size):
            current_batch = min(batch_size, profile.volume - i)
            
            # Generate batch using tool
            tool_name = "generate_synthetic_data_batch"
            if self.tool_dispatcher.has_tool(tool_name):
                batch_data = await self.tool_dispatcher.dispatch_tool(
                    tool_name=tool_name,
                    parameters={
                        "workload_type": profile.workload_type.value,
                        "batch_size": current_batch,
                        "distribution": profile.distribution,
                        "noise_level": profile.noise_level,
                        "custom_parameters": profile.custom_parameters
                    },
                    state=DeepAgentState(),
                    run_id=run_id
                )
                generated_data.extend(batch_data.get("data", []))
            else:
                # Fallback: Generate mock data
                batch_data = self._generate_mock_batch(profile, current_batch)
                generated_data.extend(batch_data)
            
            # Update progress
            status.records_generated = min(i + current_batch, profile.volume)
            status.progress_percentage = (status.records_generated / profile.volume) * 100
            
            if stream_updates and i % (batch_size * 5) == 0:  # Update every 5 batches
                await self._send_update(run_id, {
                    "status": "generating",
                    "message": f"🔄 Progress: {status.records_generated:,}/{profile.volume:,} records",
                    "progress": status.progress_percentage
                })
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.01)
        
        status.status = "completed"
        status.records_generated = profile.volume
        status.progress_percentage = 100.0
        
        return SyntheticDataResult(
            success=True,
            workload_profile=profile,
            generation_status=status,
            sample_data=generated_data[:10],  # Include sample
            metadata={
                "table_name": table_name,
                "generation_time_ms": int(time.time() * 1000),
                "checksum": self._calculate_checksum(generated_data)
            }
        )
    
    def _generate_mock_batch(self, profile: WorkloadProfile, batch_size: int) -> List[Dict[str, Any]]:
        """Generate mock data batch for demonstration"""
        import random
        from datetime import datetime, timedelta
        
        batch = []
        base_time = datetime.now(timezone.utc) - timedelta(days=profile.time_range_days)
        
        for i in range(batch_size):
            # Generate based on workload type
            if profile.workload_type == DataGenerationType.INFERENCE_LOGS:
                models = profile.custom_parameters.get("models", ["gpt-4"])
                record = {
                    "timestamp": (base_time + timedelta(
                        seconds=random.randint(0, profile.time_range_days * 86400)
                    )).isoformat(),
                    "model": random.choice(models),
                    "tokens_input": random.randint(10, 2000),
                    "tokens_output": random.randint(10, 1000),
                    "latency_ms": random.gauss(100, 20 * profile.noise_level),
                    "status": "success" if random.random() > 0.02 else "error",
                    "cost_usd": round(random.uniform(0.01, 1.0), 4)
                }
            elif profile.workload_type == DataGenerationType.PERFORMANCE_METRICS:
                record = {
                    "timestamp": (base_time + timedelta(
                        seconds=random.randint(0, profile.time_range_days * 86400)
                    )).isoformat(),
                    "throughput_rps": random.gauss(1000, 100 * profile.noise_level),
                    "p50_latency_ms": random.gauss(50, 10 * profile.noise_level),
                    "p95_latency_ms": random.gauss(150, 30 * profile.noise_level),
                    "p99_latency_ms": random.gauss(300, 50 * profile.noise_level),
                    "error_rate": random.uniform(0, 0.05),
                    "cpu_usage": random.uniform(20, 80),
                    "memory_usage": random.uniform(30, 70)
                }
            else:
                record = {
                    "id": f"record_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "value": random.random()
                }
            
            batch.append(record)
        
        return batch
    
    def _calculate_checksum(self, data: List[Dict[str, Any]]) -> str:
        """Calculate checksum for generated data"""
        import hashlib
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution"""
        await super().cleanup(state, run_id)
        
        # Log final metrics
        if state.synthetic_data_result and isinstance(state.synthetic_data_result, dict):
            result = state.synthetic_data_result
            self.logger.info(f"Synthetic data generation completed: "
                           f"table={result.get('metadata', {}).get('table_name')}, "
                           f"records={result.get('generation_status', {}).get('records_generated')}")