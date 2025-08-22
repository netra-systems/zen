"""Core spec analysis components - Base classes and data structures."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.core.exceptions_base import (
    ValidationError as ValidationException,
)


class ViolationSeverity(Enum):
    """Severity levels for spec violations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ComplianceScore:
    """Compliance score for a module or overall system."""
    module_name: str
    overall_score: float
    architecture_score: float
    type_safety_score: float
    spec_alignment_score: float
    test_coverage_score: float
    documentation_score: float
    violations: List[Dict[str, Any]]
    timestamp: datetime


@dataclass
class SpecViolation:
    """Represents a spec violation."""
    module: str
    violation_type: str
    severity: ViolationSeverity
    description: str
    file_path: str
    line_number: Optional[int]
    remediation: str


class SpecLoader:
    """Loads and parses SPEC XML files."""
    
    def __init__(self, spec_dir: Path):
        """Initialize with spec directory."""
        self.spec_dir = spec_dir
        self.specs_cache: Dict[str, ET.Element] = {}
    
    async def load_all_specs(self) -> Dict[str, ET.Element]:
        """Load all XML spec files."""
        specs = {}
        for spec_file in self.spec_dir.glob("*.xml"):
            self._load_single_spec(spec_file, specs)
        self.specs_cache = specs
        return specs
    
    def _load_single_spec(self, spec_file: Path, specs: Dict[str, ET.Element]) -> None:
        """Load a single XML spec file."""
        try:
            tree = ET.parse(spec_file)
            specs[spec_file.stem] = tree.getroot()
        except Exception as e:
            print(f"Error loading {spec_file}: {e}")
    
    def get_spec(self, name: str) -> Optional[ET.Element]:
        """Get specific spec by name."""
        return self.specs_cache.get(name)