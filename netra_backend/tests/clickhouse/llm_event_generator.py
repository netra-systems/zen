"""
LLM Event Generator
Generates realistic LLM event data for testing
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from netra_backend.tests.clickhouse.data_models import LLMEvent
from netra_backend.tests.clickhouse.generator_base import DataGeneratorBase

class LLMEventGenerator(DataGeneratorBase):
    """Generate realistic LLM events"""
    
    def _get_business_hour_timestamp(self, start_time: datetime, 
                                   time_span_hours: int) -> Optional[datetime]:
        """Generate timestamp with business hours bias"""
        hour_offset = random.random() * time_span_hours
        timestamp = start_time + timedelta(hours=hour_offset)
        hour_of_day = timestamp.hour
        
        # Business hours bias
        if 9 <= hour_of_day <= 17:
            return timestamp
        elif random.random() <= 0.3:  # 30% chance during off-hours
            return timestamp
        return None
    
    def _get_token_counts_by_workload(self, workload_type: str) -> tuple[int, int]:
        """Get realistic token counts based on workload type"""
        if workload_type == "embedding":
            return random.randint(50, 500), 0
        elif workload_type == "chat":
            return random.randint(100, 1000), random.randint(50, 500)
        elif workload_type == "code_generation":
            return random.randint(200, 2000), random.randint(100, 1500)
        return random.randint(100, 1500), random.randint(50, 1000)
    
    def _calculate_realistic_latency(self, model: str, input_tokens: int, 
                                   output_tokens: int) -> float:
        """Calculate realistic latency based on model and tokens"""
        base_latency = {LLMModel.GEMINI_2_5_FLASH.value: 2000, LLMModel.GEMINI_2_5_FLASH.value: 800, LLMModel.GEMINI_2_5_FLASH.value: 1500,
                       "gemini-pro": 1000}.get(model.split("-")[0], 1200)
        token_latency = (input_tokens + output_tokens) * 0.5
        variance = random.uniform(-200, 500)
        return base_latency + token_latency + variance
    
    def _calculate_cost_cents(self, model: str, input_tokens: int, 
                            output_tokens: int) -> float:
        """Calculate realistic cost in cents"""
        input_cost_per_1k = {LLMModel.GEMINI_2_5_FLASH.value: 0.03, LLMModel.GEMINI_2_5_FLASH.value: 0.001, 
                            LLMModel.GEMINI_2_5_FLASH.value: 0.015}.get(model.split("-")[0], 0.01)
        output_cost_per_1k = input_cost_per_1k * 2
        return (input_tokens * input_cost_per_1k + output_tokens * output_cost_per_1k) / 10
    
    def _create_llm_event_metadata(self, success: bool) -> Dict[str, Any]:
        """Create realistic LLM event metadata"""
        return {
            "session_id": str(uuid.uuid4()),
            "api_version": random.choice(["v1", "v2"]),
            "retry_count": 0 if success else random.randint(1, 3),
            "cache_hit": random.random() > 0.7
        }
    
    def _create_llm_event(self, timestamp: datetime, model: str, workload_type: str,
                         input_tokens: int, output_tokens: int, success: bool, i: int) -> LLMEvent:
        """Create a single LLM event"""
        return LLMEvent(
            timestamp=timestamp,
            event_id=str(uuid.uuid4()),
            user_id=random.randint(1, 100),
            workload_id=f"wl_{random.randint(1000, 9999)}",
            model=model,
            request_id=str(uuid.uuid4()),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=self._calculate_realistic_latency(model, input_tokens, output_tokens),
            cost_cents=self._calculate_cost_cents(model, input_tokens, output_tokens),
            success=success,
            temperature=random.choice([0.0, 0.3, 0.5, 0.7, 1.0]),
            workload_type=workload_type,
            prompt=f"Sample prompt for {workload_type} task {i}",
            response=f"Sample response for {workload_type} task {i}" if success else "Error: Request failed",
            metadata=self._create_llm_event_metadata(success)
        )
    
    def generate_llm_events(self, count: int, start_time: Optional[datetime] = None,
                           time_span_hours: int = 24) -> List[LLMEvent]:
        """Generate realistic LLM events"""
        if not start_time:
            start_time = datetime.now() - timedelta(hours=time_span_hours)
        
        events = []
        for i in range(count):
            timestamp = self._get_business_hour_timestamp(start_time, time_span_hours)
            if not timestamp:
                continue
                
            model = random.choice(self.models)
            workload_type = random.choice(self.workload_types)
            input_tokens, output_tokens = self._get_token_counts_by_workload(workload_type)
            success = random.random() > 0.05  # 95% success rate
            
            event = self._create_llm_event(timestamp, model, workload_type, 
                                         input_tokens, output_tokens, success, i)
            events.append(event)
        
        return sorted(events, key=lambda x: x.timestamp)