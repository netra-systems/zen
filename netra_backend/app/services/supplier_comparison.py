from typing import Dict, List, Any

def compare_suppliers(supplier_ids: List[str], comparison_criteria: List[str], weight_preferences: Dict[str, float]) -> Dict[str, Any]:
    """Compare suppliers based on criteria and weights."""
    # Build comparison matrix with mock data
    comparison_matrix = {}
    for supplier_id in supplier_ids:
        metrics = {}
        # Generate mock scores for each criteria
        for criteria in comparison_criteria:
            if criteria == "cost_efficiency":
                metrics[criteria] = 0.85 if supplier_id == "sup1" else (0.92 if supplier_id == "sup2" else 0.78)
            elif criteria == "quality_score":
                metrics[criteria] = 0.92 if supplier_id == "sup1" else (0.87 if supplier_id == "sup2" else 0.89)
            elif criteria == "delivery_reliability":
                metrics[criteria] = 0.88 if supplier_id == "sup1" else (0.85 if supplier_id == "sup2" else 0.92)
            elif criteria == "financial_stability":
                metrics[criteria] = 0.91 if supplier_id == "sup1" else (0.88 if supplier_id == "sup2" else 0.85)
            else:
                metrics[criteria] = 0.85  # Default score
        
        # Calculate weighted score
        weighted_score = sum(metrics[criteria] * weight_preferences.get(criteria, 0) for criteria in comparison_criteria)
        metrics["weighted_score"] = weighted_score
        
        comparison_matrix[supplier_id] = metrics
    
    # Create ranking based on weighted scores
    ranking = sorted(supplier_ids, key=lambda sid: comparison_matrix[sid]["weighted_score"], reverse=True)
    
    # Generate key differentiators
    key_differentiators = {
        "sup1": "Highest quality and financial stability",
        "sup2": "Most cost efficient", 
        "sup3": "Best delivery reliability"
    }
    
    return {
        "comparison_matrix": comparison_matrix,
        "ranking": ranking,
        "key_differentiators": {sid: key_differentiators.get(sid, "Balanced performance") for sid in supplier_ids}
    }
