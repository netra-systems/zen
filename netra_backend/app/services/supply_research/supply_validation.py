"""
Supply Validation - Data validation logic for supply items
"""

from typing import Dict, List, Any, Tuple
from decimal import Decimal

from netra_backend.app.logging_config import central_logger as logger


class SupplyValidation:
    """Handles validation of supply data before storage"""
    
    def _validate_required_fields(self, data: Dict[str, Any]) -> List[str]:
        """Validate required fields are present"""
        errors = []
        required = ["provider", "model_name"]
        for field in required:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")
        return errors
    
    def _get_field_label(self, field: str) -> str:
        """Get human-readable field label"""
        return field.replace('pricing_', '').title()
    
    def _validate_pricing_range(self, val: Decimal, field: str, errors: List[str]) -> None:
        """Validate pricing value range"""
        label = self._get_field_label(field)
        if val < 0:
            errors.append(f"{label} pricing cannot be negative")
        if val > 10000:
            errors.append(f"{label} pricing seems unrealistically high")
    
    def _validate_pricing_field(self, data: Dict[str, Any], field: str, errors: List[str]) -> None:
        """Validate a pricing field"""
        if field in data:
            try:
                val = Decimal(str(data[field]))
                self._validate_pricing_range(val, field, errors)
            except:
                errors.append(f"Invalid {field.replace('pricing_', '')} pricing format")
    
    def _validate_pricing_fields(self, data: Dict[str, Any]) -> List[str]:
        """Validate pricing fields"""
        errors = []
        self._validate_pricing_field(data, "pricing_input", errors)
        self._validate_pricing_field(data, "pricing_output", errors)
        return errors
    
    def _validate_context_window_range(self, val: int, errors: List[str]) -> None:
        """Validate context window value range"""
        if val < 0:
            errors.append("Context window cannot be negative")
        if val > 10000000:  # 10M tokens seems like a reasonable upper limit
            errors.append("Context window seems unrealistically large")
    
    def _validate_context_window(self, data: Dict[str, Any]) -> List[str]:
        """Validate context window field"""
        errors = []
        if "context_window" in data:
            try:
                val = int(data["context_window"])
                self._validate_context_window_range(val, errors)
            except:
                errors.append("Invalid context window format")
        return errors
    
    def _validate_confidence_range(self, val: float, errors: List[str]) -> None:
        """Validate confidence score range"""
        if val < 0 or val > 1:
            errors.append("Confidence score must be between 0 and 1")
    
    def _validate_confidence_score(self, data: Dict[str, Any]) -> List[str]:
        """Validate confidence score field"""
        errors = []
        if "confidence_score" in data:
            try:
                val = float(data["confidence_score"])
                self._validate_confidence_range(val, errors)
            except:
                errors.append("Invalid confidence score format")
        return errors
    
    def _validate_availability_status(self, data: Dict[str, Any]) -> List[str]:
        """Validate availability status field"""
        errors = []
        if "availability_status" in data:
            valid_statuses = ["available", "deprecated", "preview", "waitlist"]
            if data["availability_status"] not in valid_statuses:
                errors.append(f"Invalid availability status. Must be one of: {valid_statuses}")
        return errors
    
    def _collect_all_validation_errors(self, data: Dict[str, Any]) -> List[str]:
        """Collect validation errors from all validation methods"""
        errors = []
        errors.extend(self._validate_required_fields(data))
        errors.extend(self._validate_pricing_fields(data))
        errors.extend(self._validate_context_window(data))
        errors.extend(self._validate_confidence_score(data))
        errors.extend(self._validate_availability_status(data))
        return errors
    
    def validate_supply_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate supply data before storage"""
        errors = self._collect_all_validation_errors(data)
        return len(errors) == 0, errors