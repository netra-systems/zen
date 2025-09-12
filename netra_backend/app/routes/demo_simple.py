"""Simple demo endpoint that works without complex dependencies."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/demo", tags=["demo"])

class SimpleDemoChatRequest(BaseModel):
    message: str
    industry: str = "technology"  
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class SimpleDemoChatResponse(BaseModel):
    response: str
    agents_involved: list
    optimization_metrics: dict
    session_id: str

@router.post("/simple-chat", response_model=SimpleDemoChatResponse)
async def simple_demo_chat(request: SimpleDemoChatRequest) -> SimpleDemoChatResponse:
    """Simple demo chat that returns a proper optimization response."""
    
    # Generate session ID if not provided
    session_id = request.session_id or f"demo-{uuid.uuid4()}"
    
    # Generate industry-specific response
    industry_responses = {
        "technology": """Based on my analysis of your AI infrastructure, I've identified several optimization opportunities:

1. **Model Selection Optimization**: By implementing intelligent model routing, you can reduce costs by 40% while maintaining quality. For instance, routing simple queries to smaller models like GPT-3.5 instead of GPT-4 can save $15,000/month.

2. **Caching Strategy**: Implementing semantic caching for repeated queries can reduce API calls by 35%, saving approximately $8,000/month.

3. **Batch Processing**: Consolidating requests into batches can improve throughput by 3x and reduce latency from 2.5s to 0.8s per request.

4. **Cost Breakdown**:
   - Current monthly spend: $50,000
   - Optimized spend: $27,000
   - Monthly savings: $23,000 (46% reduction)

Our multi-agent system will continuously monitor and optimize these parameters, ensuring you get maximum value from your AI investment.""",
        
        "healthcare": """I've analyzed your healthcare AI workloads and identified critical optimization paths:

1. **Diagnostic Model Optimization**: Switching to specialized medical models for specific tasks can improve accuracy from 88% to 95% while reducing compute costs by 30%.

2. **HIPAA-Compliant Caching**: Implementing secure, compliant caching can reduce redundant processing by 40%, saving $12,000/month.

3. **Inference Optimization**: Using model quantization and pruning can reduce latency from 500ms to 200ms without sacrificing accuracy.

4. **ROI Analysis**:
   - Current diagnostic processing cost: $35,000/month
   - Optimized cost: $21,000/month
   - Quality improvement: 7% accuracy increase
   - Patient throughput: 2.5x increase

This optimization maintains full regulatory compliance while significantly improving both cost and performance metrics.""",
        
        "financial": """Your financial AI systems show significant optimization potential:

1. **Fraud Detection Enhancement**: By optimizing model ensemble strategies, we can reduce false positives by 60% while maintaining 99.9% fraud catch rate.

2. **Real-time Processing**: Implementing stream processing optimizations can reduce transaction analysis time from 300ms to 50ms.

3. **Cost Optimization**:
   - Current infrastructure: $75,000/month
   - Optimized infrastructure: $42,000/month
   - Annual savings: $396,000

4. **Risk Scoring Improvements**: Our optimization can process 10x more transactions with the same resources while improving risk assessment accuracy by 15%.

These optimizations will directly impact your bottom line through reduced operational costs and improved fraud prevention."""
    }
    
    # Get response for industry or use default
    response_text = industry_responses.get(
        request.industry, 
        industry_responses["technology"]
    )
    
    # Create optimization metrics
    optimization_metrics = {
        "cost_reduction": 46,
        "latency_improvement": 68,
        "throughput_increase": 300,
        "accuracy_improvement": 7,
        "monthly_savings": 23000,
        "roi_months": 3,
        "optimization_score": 92
    }
    
    # List of agents that would be involved
    agents_involved = [
        "TriageAgent",
        "DataAnalysisAgent",
        "OptimizationAgent",
        "CostAnalysisAgent",
        "ReportingAgent"
    ]
    
    return SimpleDemoChatResponse(
        response=response_text,
        agents_involved=agents_involved,
        optimization_metrics=optimization_metrics,
        session_id=session_id
    )