"""
Tool Handler Helper Functions

Helper functions to support individual tool handlers while maintaining 
the 8-line function limit and modular architecture.
"""
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.db.models_postgres import User


def build_corpus_create_params_base(kwargs: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Build base parameters for corpus creation"""
    domain = kwargs.get('domain', 'general')
    return {
        "name": kwargs.get('name', f'corpus_{domain}'),
        "domain": domain,
        "user_id": user.id
    }


def add_corpus_description(params: Dict[str, Any], kwargs: Dict[str, Any]) -> None:
    """Add description to corpus parameters"""
    domain = params["domain"]
    params["description"] = kwargs.get('description', f'Corpus for {domain} domain')


def extract_corpus_service_params(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Extract corpus service-specific parameters"""
    return {
        "preset": kwargs.get('preset'),
        "corpus_id": kwargs.get('corpus_id'),
        "count": kwargs.get('count', 10)
    }


def add_user_id_to_params(params: Dict[str, Any], user: User) -> None:
    """Add user ID to parameters"""
    params["user_id"] = user.id


def check_corpus_id_required(corpus_id: Optional[str]) -> None:
    """Check if corpus_id is provided when required"""
    if not corpus_id:
        raise ValueError("corpus_id required for validation")


def check_email_required(email: Optional[str]) -> None:
    """Check if email is provided when required"""
    if not email:
        raise ValueError("email required for user creation")


def build_user_create_params(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Build parameters for user creation"""
    return {
        "email": kwargs.get('email'),
        "role": kwargs.get('role', 'standard_user')
    }


def check_user_permission_params(user_email: Optional[str], permission: Optional[str]) -> None:
    """Check if user permission parameters are provided"""
    if not user_email or not permission:
        raise ValueError("user_email and permission required")


def extract_log_analysis_params(kwargs: Dict[str, Any]) -> Tuple[str, str]:
    """Extract log analysis parameters"""
    query = kwargs.get('query', '')
    time_range = kwargs.get('time_range', '1h')
    return query, time_range


def build_debug_service_params(user: User) -> Dict[str, Any]:
    """Build parameters for debug service"""
    return {
        "component": 'logs',
        "include_logs": True,
        "user_id": user.id
    }


def create_log_analysis_result(query: str, time_range: str, result: dict) -> Dict[str, Any]:
    """Create log analysis result response"""
    return {
        "status": "success",
        "query": query,
        "time_range": time_range,
        "logs": result.get('logs', []),
        "summary": f"Log analysis for query: {query}"
    }


def check_setting_name_required(setting_name: Optional[str]) -> None:
    """Check if setting name is provided when required"""
    if not setting_name:
        raise ValueError("setting_name required")


def create_setting_update_result(setting_name: str, value: Any) -> Dict[str, Any]:
    """Create setting update result"""
    return {
        "status": "success",
        "setting": setting_name,
        "value": value,
        "message": "Setting update simulated (would require restart)"
    }


def check_tool_executor_exists(executor) -> None:
    """Check if tool executor exists"""
    if not executor:
        raise ValueError("Unknown admin tool")


def create_synthetic_success_response(result: Any) -> Dict[str, Any]:
    """Create synthetic data generation success response"""
    return {"status": "success", "data": result}


def create_corpus_success_response(result: Any) -> Dict[str, Any]:
    """Create corpus operation success response"""
    return {"status": "success", "corpus": result}


def create_corpus_list_response(corpora: Any) -> Dict[str, Any]:
    """Create corpus list response"""
    return {"status": "success", "corpora": corpora}


def create_corpus_validation_response(corpus_id: str) -> Dict[str, Any]:
    """Create corpus validation response"""
    return {"status": "success", "valid": True, "corpus_id": corpus_id}


def create_user_success_response(result: Any) -> Dict[str, Any]:
    """Create user operation success response"""
    return {"status": "success", "user": result}


def create_permission_grant_response(success: bool) -> Dict[str, Any]:
    """Create permission grant response"""
    return {"status": "success" if success else "error", "granted": success}


def create_presets_list_response(presets: Any) -> Dict[str, Any]:
    """Create presets list response"""
    return {"status": "success", "presets": presets}