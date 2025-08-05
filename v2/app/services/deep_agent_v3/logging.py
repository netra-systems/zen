import logging
from typing import Dict, Any, List

class RunLogger:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.logs: List[Dict[str, Any]] = []

    def log(self, event: str, data: Dict[str, Any]):
        log_entry = {
            "event": event,
            "data": data
        }
        self.logs.append(log_entry)
        logging.info(f"Run ID [{self.run_id}] - Event: {event}, Data: {data}")

    def get_logs(self) -> List[Dict[str, Any]]:
        return self.logs
