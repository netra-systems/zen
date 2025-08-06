import os
import json
import time
from typing import Dict, Any, Optional

class JobStore:
    def __init__(self, store_dir: str = "app/data/generated/jobs"):
        self.store_dir = store_dir
        os.makedirs(self.store_dir, exist_ok=True)

    def _get_job_path(self, job_id: str) -> str:
        return os.path.join(self.store_dir, f"{job_id}.json")

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        job_path = self._get_job_path(job_id)
        if not os.path.exists(job_path):
            return None
        try:
            with open(job_path, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            return None

    def update(self, job_id: str, status: str, **kwargs):
        job_data = self.get(job_id) or {}
        
        job_data['job_id'] = job_id
        job_data['status'] = status
        job_data['last_updated'] = time.time()
        job_data.update(kwargs)

        job_path = self._get_job_path(job_id)
        try:
            with open(job_path, 'w') as f:
                json.dump(job_data, f, indent=4)
        except IOError:
            # Handle exceptions
            pass

    def set(self, job_id: str, job_data: Dict[str, Any]):
        job_data['last_updated'] = time.time()
        job_path = self._get_job_path(job_id)
        try:
            with open(job_path, 'w') as f:
                json.dump(job_data, f, indent=4)
        except IOError:
            # Handle exceptions
            pass

# Singleton instance
job_store = JobStore()
