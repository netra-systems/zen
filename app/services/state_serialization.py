"""State Serialization and Validation Service

This module handles state serialization, deserialization, and validation
following the 8-line function limit and modular design principles.
"""

import json
import gzip
import pickle
from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel
from app.schemas.agent_state import (
    SerializationFormat, StateValidationResult
)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder for datetime objects and Pydantic models."""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, BaseModel):
            return obj.model_dump()
        return super().default(obj)


class StateSerializer:
    """Handles state serialization with compression."""
    
    def serialize(self, state_data: Dict[str, Any], 
                 format_type: SerializationFormat) -> bytes:
        """Serialize state data in specified format."""
        if format_type == SerializationFormat.JSON:
            return self._serialize_json(state_data)
        elif format_type == SerializationFormat.PICKLE:
            return pickle.dumps(state_data)
        elif format_type == SerializationFormat.COMPRESSED_JSON:
            return self._compress_json(state_data)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def deserialize(self, serialized_data: bytes, 
                   format_type: SerializationFormat) -> Dict[str, Any]:
        """Deserialize state data from specified format."""
        if format_type == SerializationFormat.JSON:
            return json.loads(serialized_data.decode('utf-8'))
        elif format_type == SerializationFormat.PICKLE:
            return pickle.loads(serialized_data)
        elif format_type == SerializationFormat.COMPRESSED_JSON:
            return self._decompress_json(serialized_data)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _serialize_json(self, state_data: Dict[str, Any]) -> bytes:
        """Serialize data to JSON format."""
        return json.dumps(state_data, cls=DateTimeEncoder).encode('utf-8')
    
    def _compress_json(self, state_data: Dict[str, Any]) -> bytes:
        """Compress JSON data using gzip."""
        json_data = self._serialize_json(state_data)
        return gzip.compress(json_data)
    
    def _decompress_json(self, compressed_data: bytes) -> Dict[str, Any]:
        """Decompress gzipped JSON data."""
        json_data = gzip.decompress(compressed_data).decode('utf-8')
        return json.loads(json_data)


class StateValidator:
    """Validates agent state integrity."""
    
    def validate_state(self, state_data: Dict[str, Any]) -> StateValidationResult:
        """Validate state data integrity."""
        errors = []
        warnings = []
        missing_fields = []
        corrupted_fields = []
        
        self._check_required_fields(state_data, missing_fields)
        self._check_data_integrity(state_data, corrupted_fields)
        self._check_field_types(state_data, errors)
        
        return self._create_validation_result(
            errors, warnings, missing_fields, corrupted_fields)
    
    def _check_required_fields(self, state_data: Dict[str, Any], 
                              missing_fields: List[str]) -> None:
        """Check for required fields in state data."""
        required_fields = ['user_request', 'step_count', 'metadata']
        for field in required_fields:
            if field not in state_data:
                missing_fields.append(field)
    
    def _check_data_integrity(self, state_data: Dict[str, Any], 
                             corrupted_fields: List[str]) -> None:
        """Check data integrity of state fields."""
        try:
            self._validate_step_count(state_data, corrupted_fields)
            self._validate_metadata(state_data, corrupted_fields)
        except Exception:
            corrupted_fields.append('general_corruption')
    
    def _validate_step_count(self, state_data: Dict[str, Any], 
                            corrupted_fields: List[str]) -> None:
        """Validate step_count field integrity."""
        if 'step_count' in state_data:
            if not isinstance(state_data['step_count'], int):
                corrupted_fields.append('step_count')
    
    def _validate_metadata(self, state_data: Dict[str, Any], 
                          corrupted_fields: List[str]) -> None:
        """Validate metadata field integrity."""
        if 'metadata' in state_data:
            if not isinstance(state_data['metadata'], dict):
                corrupted_fields.append('metadata')
    
    def _check_field_types(self, state_data: Dict[str, Any], 
                          errors: List[str]) -> None:
        """Check field type consistency."""
        if 'step_count' in state_data:
            step_count = state_data['step_count']
            if not isinstance(step_count, int) or step_count < 0:
                errors.append('Invalid step_count: must be non-negative integer')
    
    def _create_validation_result(self, errors: List[str], warnings: List[str],
                                 missing_fields: List[str], 
                                 corrupted_fields: List[str]) -> StateValidationResult:
        """Create validation result with calculated score."""
        is_valid = len(errors) == 0 and len(corrupted_fields) == 0
        validation_score = self._calculate_validation_score(
            errors, warnings, missing_fields, corrupted_fields)
        
        return StateValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_fields=missing_fields,
            corrupted_fields=corrupted_fields,
            validation_score=validation_score
        )
    
    def _calculate_validation_score(self, errors: List[str], warnings: List[str],
                                   missing_fields: List[str], 
                                   corrupted_fields: List[str]) -> float:
        """Calculate validation score (0.0 to 1.0)."""
        total_issues = len(errors) + len(warnings) + len(missing_fields) + len(corrupted_fields)
        if total_issues == 0:
            return 1.0
        # Weighted scoring: errors=0.4, corrupted=0.3, missing=0.2, warnings=0.1
        score = self._calculate_weighted_score(errors, warnings, missing_fields, corrupted_fields)
        return max(0.0, min(1.0, score))
    
    def _calculate_weighted_score(self, errors: List[str], warnings: List[str],
                                 missing_fields: List[str], 
                                 corrupted_fields: List[str]) -> float:
        """Calculate weighted validation score."""
        score = 1.0 - (len(errors) * 0.4 + len(corrupted_fields) * 0.3 + 
                      len(missing_fields) * 0.2 + len(warnings) * 0.1) / 10
        return score