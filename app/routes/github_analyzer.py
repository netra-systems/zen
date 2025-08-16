"""GitHub Analyzer API Routes.

API endpoints for GitHub code analysis agent.
"""

from typing import Dict, Any, List
from datetime import datetime
import uuid
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from app.auth.auth_dependencies import get_current_user
from app.schemas.github_analyzer import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
    AIOperationsMap
)
from app.schemas.core_models import User
from app.agents.github_analyzer import GitHubAnalyzerAgent
from app.agents.supervisor.agent_execution_core import AgentExecutionCore
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher
from app.logging_config import central_logger as logger
from app.db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/api/github", tags=["github_analyzer"])

# Store for analysis status (in production, use database)
analysis_store: Dict[str, Dict[str, Any]] = {}


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_repository(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> AnalysisResponse:
    """Analyze a GitHub repository for AI operations."""
    
    # Validate user permissions
    if not current_user.has_role("corpus_admin"):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions for repository analysis"
        )
    
    # Generate analysis ID
    analysis_id = str(uuid.uuid4())
    
    # Store initial status
    analysis_store[analysis_id] = {
        "status": "started",
        "progress": 0,
        "message": "Initializing analysis",
        "started_at": datetime.utcnow(),
        "repository_url": request.repository_url,
        "user_id": current_user.id
    }
    
    # Start analysis in background
    background_tasks.add_task(
        run_analysis,
        analysis_id,
        request,
        current_user.id,
        db
    )
    
    return AnalysisResponse(
        success=True,
        analysis_id=analysis_id,
        repository_url=request.repository_url,
        analyzed_at=datetime.utcnow(),
        status="started"
    )


@router.get("/analysis/{analysis_id}/status", response_model=AnalysisStatus)
async def get_analysis_status(
    analysis_id: str,
    current_user: User = Depends(get_current_user)
) -> AnalysisStatus:
    """Get status of a repository analysis."""
    
    if analysis_id not in analysis_store:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found"
        )
    
    status_data = analysis_store[analysis_id]
    
    # Verify user owns this analysis
    if status_data.get("user_id") != current_user.id:
        if not current_user.has_role("admin"):
            raise HTTPException(
                status_code=403,
                detail="Access denied to this analysis"
            )
    
    return AnalysisStatus(
        analysis_id=analysis_id,
        status=status_data["status"],
        progress=status_data.get("progress", 0),
        message=status_data.get("message", ""),
        started_at=status_data["started_at"],
        completed_at=status_data.get("completed_at")
    )


@router.get("/analysis/{analysis_id}/results", response_model=AnalysisResponse)
async def get_analysis_results(
    analysis_id: str,
    current_user: User = Depends(get_current_user)
) -> AnalysisResponse:
    """Get results of a completed repository analysis."""
    
    if analysis_id not in analysis_store:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found"
        )
    
    status_data = analysis_store[analysis_id]
    
    # Verify user owns this analysis
    if status_data.get("user_id") != current_user.id:
        if not current_user.has_role("admin"):
            raise HTTPException(
                status_code=403,
                detail="Access denied to this analysis"
            )
    
    if status_data["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not completed. Current status: {status_data['status']}"
        )
    
    return AnalysisResponse(
        success=True,
        analysis_id=analysis_id,
        repository_url=status_data["repository_url"],
        analyzed_at=status_data["completed_at"],
        result=status_data.get("result"),
        status="completed"
    )


async def run_analysis(
    analysis_id: str,
    request: AnalysisRequest,
    user_id: str,
    db: AsyncSession
) -> None:
    """Run repository analysis in background."""
    
    try:
        # Update status
        analysis_store[analysis_id]["status"] = "running"
        analysis_store[analysis_id]["progress"] = 10
        analysis_store[analysis_id]["message"] = "Initializing agent"
        
        # Initialize components
        llm_manager = LLMManager()
        tool_dispatcher = ToolDispatcher()
        
        # Create analyzer agent
        analyzer = GitHubAnalyzerAgent(llm_manager, tool_dispatcher)
        
        # Update progress
        analysis_store[analysis_id]["progress"] = 20
        analysis_store[analysis_id]["message"] = "Starting analysis"
        
        # Execute analysis
        from app.agents.state import DeepAgentState
        
        state = DeepAgentState()
        context = {
            "repository_url": request.repository_url,
            "output_format": request.output_format,
            "scan_depth": request.scan_depth,
            "include_security": request.include_security
        }
        
        # Run analysis
        result = await analyzer.execute(state, context)
        
        # Update final status
        analysis_store[analysis_id]["status"] = "completed"
        analysis_store[analysis_id]["progress"] = 100
        analysis_store[analysis_id]["message"] = "Analysis completed"
        analysis_store[analysis_id]["completed_at"] = datetime.utcnow()
        
        if result.success:
            analysis_store[analysis_id]["result"] = result.data
        else:
            analysis_store[analysis_id]["status"] = "failed"
            analysis_store[analysis_id]["error"] = result.error
        
        # Cleanup
        await analyzer.github_client.cleanup()
        
        logger.info(f"Analysis {analysis_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Analysis {analysis_id} failed: {str(e)}")
        
        analysis_store[analysis_id]["status"] = "failed"
        analysis_store[analysis_id]["error"] = str(e)
        analysis_store[analysis_id]["completed_at"] = datetime.utcnow()


@router.get("/analyses", response_model=List[Dict[str, Any]])
async def list_analyses(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """List all analyses for the current user."""
    
    user_analyses = []
    
    for analysis_id, data in analysis_store.items():
        if data.get("user_id") == current_user.id or current_user.has_role("admin"):
            user_analyses.append({
                "analysis_id": analysis_id,
                "repository_url": data["repository_url"],
                "status": data["status"],
                "started_at": data["started_at"],
                "completed_at": data.get("completed_at")
            })
    
    return user_analyses


@router.delete("/analysis/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete an analysis."""
    
    if analysis_id not in analysis_store:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found"
        )
    
    status_data = analysis_store[analysis_id]
    
    # Verify user owns this analysis
    if status_data.get("user_id") != current_user.id:
        if not current_user.has_role("admin"):
            raise HTTPException(
                status_code=403,
                detail="Access denied to this analysis"
            )
    
    del analysis_store[analysis_id]
    
    return {"message": "Analysis deleted successfully"}