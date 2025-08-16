"""Circuit breaker specific utilities."""

from typing import Dict, Any, List


def _circuit_matches_keywords(name: str, keywords: List[str]) -> bool:
    """Check if circuit name matches any keyword."""
    return any(keyword in name.lower() for keyword in keywords)


def filter_circuits_by_keywords(
    all_circuits: Dict[str, Dict[str, Any]], 
    keywords: List[str]
) -> Dict[str, Dict[str, Any]]:
    """Filter circuits by keywords."""
    return {
        name: status for name, status in all_circuits.items()
        if _circuit_matches_keywords(name, keywords)
    }


def filter_llm_circuits(all_status: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Filter LLM-related circuits."""
    return filter_circuits_by_keywords(all_status, ["llm"])


def filter_database_circuits(all_status: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Filter database-related circuits."""
    return filter_circuits_by_keywords(
        all_status, 
        ["postgres", "clickhouse", "db_"]
    )


def filter_api_circuits(all_status: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Filter external API circuits."""
    return filter_circuits_by_keywords(
        all_status, 
        ["http_", "api", "google", "openai"]
    )


def _get_categorized_circuit_names(service_health: Dict[str, Dict[str, Any]]) -> set:
    """Extract all categorized circuit names."""
    categorized_names = set()
    for circuits in service_health.values():
        categorized_names.update(circuits.keys())
    return categorized_names


def _get_uncategorized_circuits(
    all_status: Dict[str, Dict[str, Any]], 
    categorized_names: set
) -> Dict[str, Any]:
    """Get circuits not in any category."""
    return {
        name: status for name, status in all_status.items()
        if name not in categorized_names
    }


def _build_initial_categories(all_status: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Build initial service categories."""
    return {
        "llm": filter_llm_circuits(all_status),
        "database": filter_database_circuits(all_status),
        "external_apis": filter_api_circuits(all_status),
        "other": {}
    }


def categorize_circuits(all_status: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Categorize circuits by service type."""
    service_health = _build_initial_categories(all_status)
    categorized_names = _get_categorized_circuit_names(service_health)
    service_health["other"] = _get_uncategorized_circuits(all_status, categorized_names)
    return service_health


def build_service_summary(service_health: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Build service health summary."""
    from .response_builders import _assess_service_health
    return {
        service: {
            "circuit_count": len(circuits),
            "overall_health": _assess_service_health(circuits),
            "circuits": circuits
        }
        for service, circuits in service_health.items()
    }