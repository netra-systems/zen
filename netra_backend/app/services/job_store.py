import json
from typing import Any, Dict


class JobStore:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}

    async def set(self, job_id: str, data: Dict[str, Any]):
        self._jobs[job_id] = data

    async def get(self, job_id: str) -> Dict[str, Any]:
        return self._jobs.get(job_id)

    async def update(self, job_id: str, status: str, **kwargs):
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = status
            self._jobs[job_id].update(kwargs)

job_store = JobStore()