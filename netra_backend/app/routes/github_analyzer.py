"""GitHub Analyzer API Routes.

API endpoints for GitHub code analysis agent.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.github_analyzer import GitHubAnalyzerService
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
# SSOT COMPLIANCE: Import from the facade (already SSOT-compliant)
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.database import get_db as get_db_session
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.core_models import User
from netra_backend.app.schemas.github_analyzer import (
    AIOperationsMap,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
)

router = APIRouter(prefix="/api/github", tags=["github_analyzer"])

# Store for analysis status (in production, use database)
analysis_store: Dict[str, Dict[str, Any]] = {}


def _validate_user_permissions(current_user: User) -> None:
    """Validate user has required permissions for analysis."""
    if not current_user.has_role("corpus_admin"):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions for repository analysis"
        )

def _store_analysis_initial_status(analysis_id: str, request: AnalysisRequest, user_id: str) -> None:
    """Store initial analysis status."""
    analysis_store[analysis_id] = {
        "status": "started", "progress": 0, "message": "Initializing analysis",
        "started_at": datetime.now(timezone.utc), "repository_url": request.repository_url,
        "user_id": user_id
    }

def _start_background_analysis(
    background_tasks: BackgroundTasks, analysis_id: str, request: AnalysisRequest,
    user_id: str, db: AsyncSession
) -> None:
    """Start analysis in background task."""
    background_tasks.add_task(run_analysis, analysis_id, request, user_id, db)

def _build_analysis_response(analysis_id: str, request: AnalysisRequest) -> AnalysisResponse:
    """Build analysis response."""
    return AnalysisResponse(
        success=True, analysis_id=analysis_id, repository_url=request.repository_url,
        analyzed_at=datetime.now(timezone.utc), status="started"
    )

async def _process_analysis_request(request: AnalysisRequest, background_tasks: BackgroundTasks, current_user: User, db: AsyncSession) -> AnalysisResponse:
    """Process analysis request with validation and background task setup."""
    _validate_user_permissions(current_user)
    analysis_id = str(uuid.uuid4())
    _store_analysis_initial_status(analysis_id, request, current_user.id)
    _start_background_analysis(background_tasks, analysis_id, request, current_user.id, db)
    return _build_analysis_response(analysis_id, request)

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_repository(
    request: AnalysisRequest, background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)
) -> AnalysisResponse:
    """Analyze a GitHub repository for AI operations."""
    return await _process_analysis_request(request, background_tasks, current_user, db)


def _validate_analysis_exists(analysis_id: str) -> None:
    """Validate analysis exists in store."""
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail="Analysis not found")

def _validate_analysis_access(status_data: Dict[str, Any], current_user: User) -> None:
    """Validate user has access to analysis."""
    if status_data.get("user_id") != current_user.id:
        if not current_user.has_role("admin"):
            raise HTTPException(status_code=403, detail="Access denied to this analysis")

def _build_analysis_status_response(analysis_id: str, status_data: Dict[str, Any]) -> AnalysisStatus:
    """Build analysis status response."""
    return AnalysisStatus(
        analysis_id=analysis_id, status=status_data["status"],
        progress=status_data.get("progress", 0), message=status_data.get("message", ""),
        started_at=status_data["started_at"], completed_at=status_data.get("completed_at")
    )

@router.get("/analysis/{analysis_id}/status", response_model=AnalysisStatus)
async def get_analysis_status(
    analysis_id: str, current_user: User = Depends(get_current_user)
) -> AnalysisStatus:
    """Get status of a repository analysis."""
    _validate_analysis_exists(analysis_id)
    status_data = analysis_store[analysis_id]
    _validate_analysis_access(status_data, current_user)
    return _build_analysis_status_response(analysis_id, status_data)


def _validate_analysis_completed(status_data: Dict[str, Any]) -> None:
    """Validate analysis is completed."""
    if status_data["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not completed. Current status: {status_data['status']}"
        )

def _build_analysis_results_response(analysis_id: str, status_data: Dict[str, Any]) -> AnalysisResponse:
    """Build analysis results response."""
    return AnalysisResponse(
        success=True, analysis_id=analysis_id, repository_url=status_data["repository_url"],
        analyzed_at=status_data["completed_at"], result=status_data.get("result"),
        status="completed"
    )

async def _get_validated_analysis_results(analysis_id: str, current_user: User) -> AnalysisResponse:
    """Get validated analysis results with access checks."""
    _validate_analysis_exists(analysis_id)
    status_data = analysis_store[analysis_id]
    _validate_analysis_access(status_data, current_user)
    _validate_analysis_completed(status_data)
    return _build_analysis_results_response(analysis_id, status_data)

@router.get("/analysis/{analysis_id}/results", response_model=AnalysisResponse)
async def get_analysis_results(analysis_id: str, current_user: User = Depends(get_current_user)) -> AnalysisResponse:
    """Get results of a completed repository analysis."""
    return await _get_validated_analysis_results(analysis_id, current_user)


async def _run_analysis_workflow(
    analysis_id: str, request: AnalysisRequest, analyzer: GitHubAnalyzerService
) -> None:
    """Run the analysis workflow."""
    result = await _execute_repository_analysis(analysis_id, request, analyzer)
    await _finalize_analysis_result(analysis_id, result)
    await _cleanup_analysis_resources(analyzer)
    logger.info(f"Analysis {analysis_id} completed successfully")

async def _run_analysis_safe(analysis_id: str, request: AnalysisRequest, analyzer: GitHubAnalyzerService) -> None:
    """Run analysis with error handling."""
    try:
        await _run_analysis_workflow(analysis_id, request, analyzer)
    except Exception as e:
        await _handle_analysis_error(analysis_id, e)

async def run_analysis(analysis_id: str, request: AnalysisRequest, user_id: str, db: AsyncSession) -> None:
    """Run repository analysis in background."""
    analyzer = await _initialize_analysis_components(analysis_id)
    await _run_analysis_safe(analysis_id, request, analyzer)


async def _initialize_analysis_components(analysis_id: str) -> GitHubAnalyzerService:
    """Initialize analysis components and update progress."""
    _update_analysis_status(analysis_id, "running", 10, "Initializing service")
    llm_manager = LLMManager()
    tool_dispatcher = ToolDispatcher()
    analyzer = GitHubAnalyzerService(llm_manager, tool_dispatcher)
    _update_analysis_status(analysis_id, "running", 20, "Starting analysis")
    return analyzer


async def _setup_analysis_environment(request: AnalysisRequest) -> tuple:
    """Setup analysis state and context.
    
    SECURITY FIX: Use secure UserExecutionContext instead of vulnerable DeepAgentState.
    This prevents input injection and serialization security vulnerabilities.
    """
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.core.unified_id_manager import UnifiedIDManager
    
    # Generate secure IDs for the analysis context
    id_manager = UnifiedIDManager()
    thread_id = id_manager.generate_thread_id()
    run_id = id_manager.generate_run_id(thread_id)
    request_id = str(uuid.uuid4())
    
    # Create secure context with input validation
    secure_context = UserExecutionContext.from_request(
        user_id="github_analyzer_service",  # Service account for analysis
        thread_id=thread_id,
        run_id=run_id,
        request_id=request_id,
        agent_context={
            'operation_type': 'github_analysis',
            'repository_url': request.repository_url,
            'analysis_depth': getattr(request, 'analysis_depth', 'standard'),
            'operation_source': 'github_analyzer_api'
        },
        audit_metadata={
            'security_migration': {
                'migrated_from': 'DeepAgentState',
                'migration_date': '2025-09-10',
                'vulnerability_fix': 'github_analyzer_input_injection_serialization'
            },
            'analysis_request': {
                'repository_url': request.repository_url,
                'request_timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    context = _build_analysis_context(request)
    return secure_context, context

async def _execute_repository_analysis(analysis_id: str, request: AnalysisRequest, analyzer: GitHubAnalyzerService) -> Any:
    """Execute the repository analysis with proper context.
    
    SECURITY FIX: Now uses secure UserExecutionContext instead of vulnerable DeepAgentState.
    """
    secure_context, context = await _setup_analysis_environment(request)
    return await analyzer.execute(secure_context, context)


def _build_analysis_context(request: AnalysisRequest) -> Dict[str, Any]:
    """Build analysis context from request parameters."""
    return {
        "repository_url": request.repository_url,
        "output_format": request.output_format,
        "scan_depth": request.scan_depth,
        "include_security": request.include_security
    }


def _set_analysis_completion(analysis_id: str) -> None:
    """Set analysis completion status."""
    _update_analysis_status(analysis_id, "completed", 100, "Analysis completed")
    analysis_store[analysis_id]["completed_at"] = datetime.now(timezone.utc)

def _process_analysis_result(analysis_id: str, result: Any) -> None:
    """Process analysis result based on success status."""
    if result.success:
        analysis_store[analysis_id]["result"] = result.data
    else:
        _mark_analysis_failed(analysis_id, result.error)

async def _finalize_analysis_result(analysis_id: str, result: Any) -> None:
    """Update final analysis status based on result."""
    _set_analysis_completion(analysis_id)
    _process_analysis_result(analysis_id, result)


async def _cleanup_analysis_resources(analyzer: GitHubAnalyzerService) -> None:
    """Clean up analysis resources."""
    await analyzer.github_client.cleanup()


async def _handle_analysis_error(analysis_id: str, error: Exception) -> None:
    """Handle analysis errors and update status."""
    logger.error(f"Analysis {analysis_id} failed: {str(error)}")
    _mark_analysis_failed(analysis_id, str(error))
    analysis_store[analysis_id]["completed_at"] = datetime.now(timezone.utc)


def _update_analysis_status(analysis_id: str, status: str, progress: int, message: str) -> None:
    """Update analysis status with progress information."""
    analysis_store[analysis_id]["status"] = status
    analysis_store[analysis_id]["progress"] = progress
    analysis_store[analysis_id]["message"] = message


def _mark_analysis_failed(analysis_id: str, error: str) -> None:
    """Mark analysis as failed with error information."""
    analysis_store[analysis_id]["status"] = "failed"
    analysis_store[analysis_id]["error"] = error


def _check_user_access_to_analysis(data: Dict[str, Any], current_user: User) -> bool:
    """Check if user has access to analysis."""
    return data.get("user_id") == current_user.id or current_user.has_role("admin")

def _build_analysis_summary(analysis_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Build analysis summary for listing."""
    return {
        "analysis_id": analysis_id, "repository_url": data["repository_url"],
        "status": data["status"], "started_at": data["started_at"],
        "completed_at": data.get("completed_at")
    }

def _collect_user_analyses(current_user: User) -> List[Dict[str, Any]]:
    """Collect analyses accessible to user."""
    user_analyses = []
    for analysis_id, data in analysis_store.items():
        if _check_user_access_to_analysis(data, current_user):
            user_analyses.append(_build_analysis_summary(analysis_id, data))
    return user_analyses

@router.get("/analyses", response_model=List[Dict[str, Any]])
async def list_analyses(current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """List all analyses for the current user."""
    return _collect_user_analyses(current_user)


def _delete_analysis_from_store(analysis_id: str) -> None:
    """Delete analysis from store."""
    del analysis_store[analysis_id]

def _build_delete_response() -> Dict[str, str]:
    """Build delete success response."""
    return {"message": "Analysis deleted successfully"}

async def _delete_analysis_safe(analysis_id: str, current_user: User) -> Dict[str, str]:
    """Delete analysis with validation and access checks."""
    _validate_analysis_exists(analysis_id)
    status_data = analysis_store[analysis_id]
    _validate_analysis_access(status_data, current_user)
    _delete_analysis_from_store(analysis_id)
    return _build_delete_response()

@router.delete("/analysis/{analysis_id}")
async def delete_analysis(analysis_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    """Delete an analysis."""
    return await _delete_analysis_safe(analysis_id, current_user)