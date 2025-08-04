import logging
import uuid
from typing import Dict, Any

from app.db.models_clickhouse import AnalysisRequest
from app.services.deep_agent_v3.main import DeepAgentV3

class AnalysisRunner:
    """
    Handles fetching pre-enriched data and running the analysis pipeline.
    """
    def __init__(self, db_session: Any, llm_connector: any):
        self.db_session = db_session
        self.llm_connector = llm_connector
        logging.info("AnalysisRunner initialized.")

    async def execute(self, request: AnalysisRequest) -> Dict[str, Any]:
        """Runs the full analysis pipeline on the pre-enriched data."""
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        
        agent = DeepAgentV3(
            run_id=run_id,
            request=request,
            db_session=self.db_session,
            llm_connector=self.llm_connector
        )
        
        final_report = await agent.run_full_analysis()
        
        return {
            "run_id": run_id,
            "status": agent.status,
            "final_report": final_report
        }
