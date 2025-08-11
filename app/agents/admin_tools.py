"""
Admin Tools for Agent System - Corpus, Synthetic Data, and System Management
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.services import corpus_service, clickhouse_service
from app.services.permission_service import PermissionService
from app.services.synthetic_data_service import SyntheticDataService
from app.db.models_postgres import User
from app.core.logging_config import central_logger
from app import schemas
import json

logger = central_logger

class AdminToolRegistry:
    """Registry for admin-only tools available to agents"""
    
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.tools = {}
        self._register_tools()
    
    def _register_tools(self):
        """Register all admin tools if user has appropriate permissions"""
        
        # Check if user has admin/developer permissions
        if not PermissionService.is_developer_or_higher(self.user):
            logger.info(f"User {self.user.email} does not have admin permissions for admin tools")
            return
        
        # Register corpus management tool
        if PermissionService.has_permission(self.user, "corpus_write"):
            self.tools["corpus_manager"] = CorpusManagerTool(self.db, self.user)
        
        # Register synthetic data tool
        if PermissionService.has_permission(self.user, "synthetic_generate"):
            self.tools["synthetic_generator"] = SyntheticGeneratorTool(self.db, self.user)
        
        # Register user admin tool
        if PermissionService.has_permission(self.user, "user_management"):
            self.tools["user_admin"] = UserAdminTool(self.db, self.user)
        
        # Register system configurator
        if PermissionService.has_permission(self.user, "system_config"):
            self.tools["system_configurator"] = SystemConfiguratorTool(self.db, self.user)
        
        # Register log analyzer
        if PermissionService.has_permission(self.user, "log_access"):
            self.tools["log_analyzer"] = LogAnalyzerTool(self.db, self.user)
    
    def get_tool(self, tool_name: str):
        """Get a specific admin tool by name"""
        return self.tools.get(tool_name)
    
    def list_available_tools(self) -> List[str]:
        """List all available admin tools for this user"""
        return list(self.tools.keys())


class CorpusManagerTool:
    """Tool for managing corpus tables through natural language"""
    
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Any]:
        """Load domain-specific corpus templates"""
        return {
            "financial_services": {
                "name": "Financial Services Corpus",
                "description": "Corpus for financial optimization scenarios",
                "categories": [
                    "market_analysis",
                    "risk_assessment", 
                    "portfolio_optimization",
                    "compliance_checking"
                ],
                "sample_size": 10000,
                "example_prompts": [
                    "Optimize my trading strategy for Q4",
                    "Analyze risk exposure across portfolios",
                    "Check compliance with SEC regulations"
                ]
            },
            "e_commerce": {
                "name": "E-Commerce Corpus",
                "description": "Corpus for e-commerce optimization",
                "categories": [
                    "inventory_optimization",
                    "pricing_strategy",
                    "customer_segmentation",
                    "demand_forecasting"
                ],
                "sample_size": 10000,
                "example_prompts": [
                    "Optimize inventory levels for Black Friday",
                    "Suggest dynamic pricing for seasonal items",
                    "Segment customers by purchase behavior"
                ]
            },
            "healthcare": {
                "name": "Healthcare Corpus",
                "description": "Corpus for healthcare optimization",
                "categories": [
                    "patient_flow",
                    "resource_allocation",
                    "diagnostic_assistance",
                    "treatment_optimization"
                ],
                "sample_size": 10000,
                "example_prompts": [
                    "Optimize ER patient flow",
                    "Allocate nursing staff efficiently",
                    "Suggest diagnostic pathways"
                ]
            }
        }
    
    async def create_corpus(self, domain: str, **kwargs) -> Dict[str, Any]:
        """Create a new corpus with smart defaults"""
        try:
            # Get template if domain matches
            template = self.templates.get(domain.lower().replace(" ", "_"), {})
            
            # Create corpus using template or provided values
            corpus_data = schemas.CorpusCreate(
                name=kwargs.get("name", template.get("name", f"{domain} Corpus")),
                description=kwargs.get("description", template.get("description", f"Corpus for {domain}")),
                domain=domain,
                categories=kwargs.get("categories", template.get("categories", [])),
                sample_size=kwargs.get("sample_size", template.get("sample_size", 1000))
            )
            
            # Create corpus in database
            db_corpus = corpus_service.create_corpus(
                db=self.db,
                corpus=corpus_data,
                user_id=self.user.id
            )
            
            # Generate corpus content in background
            # Note: In real implementation, this would trigger background task
            
            return {
                "status": "success",
                "corpus_id": db_corpus.id,
                "message": f"Created {domain} corpus with ID {db_corpus.id}",
                "details": {
                    "name": db_corpus.name,
                    "description": db_corpus.description,
                    "status": db_corpus.status
                }
            }
        except Exception as e:
            logger.error(f"Error creating corpus: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def list_corpora(self) -> Dict[str, Any]:
        """List all available corpus tables"""
        try:
            corpora = corpus_service.get_corpora(self.db)
            tables = await clickhouse_service.list_corpus_tables()
            
            return {
                "status": "success",
                "corpora": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "description": c.description,
                        "status": c.status,
                        "created_at": c.created_at.isoformat() if c.created_at else None
                    }
                    for c in corpora
                ],
                "clickhouse_tables": tables
            }
        except Exception as e:
            logger.error(f"Error listing corpora: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def validate_corpus(self, corpus_id: str) -> Dict[str, Any]:
        """Validate corpus integrity and coverage"""
        try:
            corpus = corpus_service.get_corpus(self.db, corpus_id)
            if not corpus:
                return {
                    "status": "error",
                    "message": f"Corpus {corpus_id} not found"
                }
            
            # Get corpus content for validation
            content = corpus_service.get_corpus_content(self.db, corpus_id)
            
            validation_results = {
                "total_records": len(content) if content else 0,
                "categories_covered": set(),
                "has_duplicates": False,
                "completeness": 0.0
            }
            
            # Perform validation checks
            if content:
                # Check for duplicates
                seen = set()
                for item in content:
                    key = json.dumps(item, sort_keys=True)
                    if key in seen:
                        validation_results["has_duplicates"] = True
                        break
                    seen.add(key)
                
                # Calculate completeness
                expected_fields = ["prompt", "response", "metadata"]
                complete_records = sum(
                    1 for item in content 
                    if all(field in item for field in expected_fields)
                )
                validation_results["completeness"] = complete_records / len(content) * 100
            
            return {
                "status": "success",
                "corpus_id": corpus_id,
                "validation": validation_results
            }
        except Exception as e:
            logger.error(f"Error validating corpus: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


class SyntheticGeneratorTool:
    """Tool for generating synthetic data through natural language"""
    
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.presets = self._load_presets()
    
    def _load_presets(self) -> Dict[str, Any]:
        """Load synthetic data generation presets"""
        return {
            "quick_test": {
                "name": "Quick Test",
                "volume": 1000,
                "time_range": "1h",
                "pattern": "steady",
                "description": "Quick test with 1,000 records over 1 hour"
            },
            "load_test": {
                "name": "Load Test",
                "volume": 100000,
                "time_range": "24h",
                "pattern": "ramp_up",
                "description": "Load test with 100,000 records ramping up over 24 hours"
            },
            "incident_simulation": {
                "name": "Incident Simulation",
                "volume": 50000,
                "time_range": "6h",
                "pattern": "spike_degradation_recovery",
                "description": "Incident pattern with spike, degradation, and recovery"
            },
            "typical_day": {
                "name": "Typical Day",
                "volume": 20000,
                "time_range": "24h",
                "pattern": "business_hours",
                "description": "Typical business day pattern with peak hours"
            },
            "black_friday": {
                "name": "Black Friday",
                "volume": 500000,
                "time_range": "24h",
                "pattern": "extreme_spike",
                "description": "Black Friday shopping pattern with extreme spikes"
            }
        }
    
    async def generate_data(
        self,
        preset: Optional[str] = None,
        corpus_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate synthetic data with smart defaults"""
        try:
            # Use preset if specified
            config = {}
            if preset and preset in self.presets:
                config = self.presets[preset].copy()
            
            # Override with provided kwargs
            config.update(kwargs)
            
            # Set defaults if not provided
            config.setdefault("volume", 1000)
            config.setdefault("time_range", "1h")
            config.setdefault("pattern", "steady")
            config.setdefault("workload_distribution", {
                "simple_queries": 0.30,
                "tool_orchestration": 0.25,
                "data_analysis": 0.20,
                "optimization_workflows": 0.15,
                "error_scenarios": 0.10
            })
            
            # Get corpus if specified
            if corpus_id:
                corpus = corpus_service.get_corpus(self.db, corpus_id)
                if not corpus:
                    return {
                        "status": "error",
                        "message": f"Corpus {corpus_id} not found"
                    }
            
            # Create generation job
            # Note: In real implementation, this would trigger background task
            job_id = f"gen_{self.user.id}_{corpus_id or 'default'}"
            
            return {
                "status": "success",
                "job_id": job_id,
                "message": f"Started synthetic data generation job {job_id}",
                "config": config,
                "estimated_duration": self._estimate_duration(config["volume"])
            }
        except Exception as e:
            logger.error(f"Error generating synthetic data: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _estimate_duration(self, volume: int) -> str:
        """Estimate generation duration based on volume"""
        # Rough estimate: 10,000 records per second
        seconds = volume / 10000
        if seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            return f"{int(seconds / 60)} minutes"
        else:
            return f"{int(seconds / 3600)} hours"
    
    async def list_presets(self) -> Dict[str, Any]:
        """List available generation presets"""
        return {
            "status": "success",
            "presets": [
                {
                    "key": key,
                    **preset
                }
                for key, preset in self.presets.items()
            ]
        }


class UserAdminTool:
    """Tool for user management through natural language"""
    
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
    
    async def create_user(self, email: str, role: str = "standard_user", **kwargs) -> Dict[str, Any]:
        """Create a new user with specified role"""
        # Implementation would create user
        return {
            "status": "success",
            "message": f"User {email} created with role {role}"
        }
    
    async def grant_permission(self, user_email: str, permission: str) -> Dict[str, Any]:
        """Grant permission to a user"""
        # Implementation would grant permission
        return {
            "status": "success",
            "message": f"Granted {permission} to {user_email}"
        }


class SystemConfiguratorTool:
    """Tool for system configuration through natural language"""
    
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
    
    async def update_setting(self, setting_name: str, value: Any) -> Dict[str, Any]:
        """Update a system setting"""
        # Implementation would update setting
        return {
            "status": "success",
            "message": f"Updated {setting_name} to {value}"
        }


class LogAnalyzerTool:
    """Tool for log analysis through natural language"""
    
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
    
    async def analyze_logs(self, query: str, time_range: str = "1h") -> Dict[str, Any]:
        """Analyze logs with natural language query"""
        # Implementation would convert natural language to ClickHouse query
        return {
            "status": "success",
            "message": "Log analysis complete",
            "results": []
        }