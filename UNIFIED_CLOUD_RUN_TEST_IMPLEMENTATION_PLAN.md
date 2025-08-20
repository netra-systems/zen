# Unified Cloud Run Testing & Staging Validation Implementation Plan

## Executive Summary
Comprehensive plan to integrate Cloud Run local testing and staging validation into the existing Netra Apex test framework, enabling seamless testing from local Docker containers through staging deployment validation.

## Business Value Justification (BVJ)
- **Segment:** Platform/Internal
- **Business Goal:** Platform Stability, Risk Reduction, Development Velocity
- **Value Impact:** Reduces deployment failures by 80%, catches issues pre-production
- **Strategic Impact:** Enables confident rapid iteration with automated validation

## Architecture Overview

### 1. Unified Test Runner Extension
Extend `test_runner.py` to support Cloud Run testing modes:

```python
# New test levels in TEST_LEVELS
"docker": {
    "description": "Local Docker container testing",
    "purpose": "Test services in Docker before Cloud Run",
    "timeout": 600,
    "run_coverage": False
},
"staging": {
    "description": "Staging environment validation",
    "purpose": "Validate deployed staging services",
    "timeout": 900,
    "run_coverage": False,
    "requires_auth": True
}
```

### 2. Test Framework Components

#### 2.1 GCP Integration Module (`test_framework/gcp_integration/`)
```
gcp_integration/
├── __init__.py
├── log_reader.py         # Read Cloud Logging entries
├── health_monitor.py     # Monitor service health
├── deployment_validator.py # Validate deployments
├── secret_manager.py     # Access staging secrets
└── auth_handler.py       # Handle GCP authentication
```

#### 2.2 Docker Testing Module (`test_framework/docker_testing/`)
```
docker_testing/
├── __init__.py
├── compose_manager.py    # Manage docker-compose
├── container_health.py   # Check container health
├── network_validator.py  # Validate inter-service communication
└── environment_config.py # Configure test environments
```

#### 2.3 Staging Testing Module (`test_framework/staging_testing/`)
```
staging_testing/
├── __init__.py
├── endpoint_validator.py # Validate staging endpoints
├── performance_tester.py # Run performance tests
├── e2e_orchestrator.py  # Orchestrate E2E tests
└── deployment_monitor.py # Monitor deployment status
```

## Implementation Phases

### Phase 1: Foundation (Week 1)
1. **Create GCP Integration Module**
   - Implement GCP log reader using Google Cloud Logging API
   - Create authentication handler for service account
   - Build secret manager interface

2. **Extend Test Config**
   - Add staging and docker test levels
   - Configure endpoint mappings
   - Set up environment variables

### Phase 2: Docker Testing (Week 2)
1. **Docker Compose Integration**
   - Create docker-compose.test.yml for test environment
   - Implement compose manager for lifecycle control
   - Add health check validators

2. **Local Test Execution**
   - Extend test runner for docker mode
   - Implement container network validation
   - Add WebSocket testing in Docker

### Phase 3: Staging Testing (Week 3)
1. **Staging Endpoint Testing**
   - Implement endpoint discovery
   - Create health check suite
   - Add authentication flow tests

2. **GCP Log Analysis**
   - Implement log query builder
   - Create error analysis pipeline
   - Generate deployment reports

### Phase 4: Integration (Week 4)
1. **Unified Test Pipeline**
   - Create pre-deployment test suite
   - Implement post-deployment validation
   - Add continuous monitoring

2. **CI/CD Integration**
   - Update GitHub Actions workflows
   - Add staging test gates
   - Implement automatic rollback triggers

## Test Suites

### 1. Pre-Deployment Suite
```bash
# Local Docker validation
python test_runner.py --level docker --parallel

# Integration tests with Docker endpoints
python test_runner.py --level integration --docker-endpoints

# Agent tests with mock LLM
python test_runner.py --level agents --mock-llm
```

### 2. Post-Deployment Suite
```bash
# Health check validation
python test_runner.py --level staging --health-check

# Full staging validation
python test_runner.py --level staging --real-endpoints

# Performance baseline
python test_runner.py --level staging --performance
```

### 3. Continuous Monitoring
```bash
# Smoke tests every 30 minutes
python test_runner.py --level staging --smoke

# Health monitoring with alerts
python test_framework/staging_health_monitor.py --alert
```

## Configuration Files

### 1. `test_framework/config/staging.yaml`
```yaml
staging:
  project_id: netra-staging
  region: us-central1
  services:
    backend:
      name: netra-backend-staging
      url: https://netra-backend-staging-nxgsmzqtya-uc.a.run.app
      health_endpoint: /health
    frontend:
      name: netra-frontend-staging
      url: https://netra-frontend-staging-nxgsmzqtya-uc.a.run.app
      health_endpoint: /health
    auth:
      name: netra-auth-service
      url: https://netra-auth-service-nxgsmzqtya-uc.a.run.app
      health_endpoint: /health
  
  log_filters:
    errors: 'severity>=ERROR'
    websocket: 'jsonPayload.event_type="websocket"'
    agents: 'jsonPayload.agent_id!=null'
```

### 2. `docker-compose.test.yml`
```yaml
version: '3.8'
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      - TEST_MODE=true
      - DATABASE_URL=postgresql://test:test@postgres:5432/test
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend.staging
    environment:
      - REACT_APP_API_URL=http://backend:8000
    ports:
      - "3000:3000"
    depends_on:
      backend:
        condition: service_healthy

  auth:
    build:
      context: .
      dockerfile: Dockerfile.auth
    environment:
      - TEST_MODE=true
    ports:
      - "8001:8001"

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=test
      - POSTGRES_PASSWORD=test
      - POSTGRES_DB=test

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    
  redis:
    image: redis:7-alpine
```

## Key Implementation Files

### 1. `test_framework/gcp_integration/log_reader.py`
```python
from google.cloud import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class GCPLogReader:
    def __init__(self, project_id: str):
        self.client = logging.Client(project=project_id)
        
    def fetch_logs(
        self, 
        filter_str: str, 
        start_time: datetime, 
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Fetch logs from GCP with given filter."""
        if not end_time:
            end_time = datetime.utcnow()
            
        filter_with_time = f'{filter_str} AND timestamp>="{start_time.isoformat()}Z" AND timestamp<="{end_time.isoformat()}Z"'
        
        entries = self.client.list_entries(filter_=filter_with_time)
        return [self._entry_to_dict(entry) for entry in entries]
    
    def analyze_errors(self, service_name: str, duration_minutes: int = 30) -> Dict:
        """Analyze recent errors for a service."""
        start_time = datetime.utcnow() - timedelta(minutes=duration_minutes)
        filter_str = f'resource.labels.service_name="{service_name}" AND severity>=ERROR'
        
        logs = self.fetch_logs(filter_str, start_time)
        
        # Group errors by type
        error_groups = {}
        for log in logs:
            error_type = log.get('error_type', 'unknown')
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(log)
            
        return {
            'total_errors': len(logs),
            'error_groups': error_groups,
            'time_range': {
                'start': start_time.isoformat(),
                'end': datetime.utcnow().isoformat()
            }
        }
```

### 2. `test_framework/staging_testing/endpoint_validator.py`
```python
import requests
from typing import Dict, List, Tuple
import asyncio
import aiohttp

class StagingEndpointValidator:
    def __init__(self, config: Dict):
        self.config = config
        self.results = []
        
    async def validate_health_endpoints(self) -> List[Tuple[str, bool, str]]:
        """Validate all service health endpoints."""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for service_name, service_config in self.config['services'].items():
                url = f"{service_config['url']}{service_config['health_endpoint']}"
                tasks.append(self._check_health(session, service_name, url))
            
            return await asyncio.gather(*tasks)
    
    async def _check_health(
        self, 
        session: aiohttp.ClientSession, 
        service_name: str, 
        url: str
    ) -> Tuple[str, bool, str]:
        """Check health of a single service."""
        try:
            async with session.get(url, timeout=10) as response:
                is_healthy = response.status == 200
                message = await response.text() if not is_healthy else "Healthy"
                return (service_name, is_healthy, message)
        except Exception as e:
            return (service_name, False, str(e))
    
    def validate_api_contracts(self) -> Dict:
        """Validate API endpoints match expected contracts."""
        # Implementation for OpenAPI validation
        pass
```

### 3. `test_framework/docker_testing/compose_manager.py`
```python
import subprocess
import time
import yaml
from pathlib import Path
from typing import Dict, Optional

class DockerComposeManager:
    def __init__(self, compose_file: str = "docker-compose.test.yml"):
        self.compose_file = compose_file
        self.project_name = "netra-test"
        
    def start_services(self, services: Optional[List[str]] = None) -> bool:
        """Start Docker Compose services."""
        cmd = ["docker-compose", "-f", self.compose_file, "-p", self.project_name, "up", "-d"]
        if services:
            cmd.extend(services)
            
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    def wait_for_healthy(self, timeout: int = 300) -> bool:
        """Wait for all services to be healthy."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self._all_services_healthy():
                return True
            time.sleep(5)
            
        return False
    
    def _all_services_healthy(self) -> bool:
        """Check if all services are healthy."""
        cmd = ["docker-compose", "-f", self.compose_file, "-p", self.project_name, "ps"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parse output to check health status
        lines = result.stdout.strip().split('\n')[2:]  # Skip headers
        for line in lines:
            if 'unhealthy' in line.lower() or 'starting' in line.lower():
                return False
        return True
    
    def cleanup(self):
        """Stop and remove containers."""
        cmd = ["docker-compose", "-f", self.compose_file, "-p", self.project_name, "down", "-v"]
        subprocess.run(cmd, capture_output=True)
```

## GitHub Actions Integration

### `.github/workflows/staging-test.yml`
```yaml
name: Staging Tests

on:
  workflow_run:
    workflows: ["Deploy to Staging"]
    types:
      - completed

jobs:
  staging-validation:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install google-cloud-logging google-cloud-secret-manager
          
      - name: Authenticate to GCP
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_STAGING_SA_KEY }}
          
      - name: Run staging tests
        run: |
          python test_runner.py --level staging --health-check
          python test_runner.py --level staging --real-endpoints
          
      - name: Analyze deployment logs
        run: |
          python test_framework/gcp_log_reader.py --analyze-deployment
          
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: staging-test-results
          path: test_reports/
```

## Monitoring & Alerting

### 1. Continuous Health Monitoring
- Run health checks every 30 minutes via cron job
- Alert on 3 consecutive failures
- Generate daily health reports

### 2. Error Tracking
- Aggregate errors from Cloud Logging
- Group by error type and service
- Track error trends over time

### 3. Performance Monitoring
- Track API response times
- Monitor WebSocket latency
- Alert on performance degradation

## Success Metrics

1. **Deployment Success Rate:** Target >95%
2. **Mean Time to Detection (MTTD):** <5 minutes for staging issues
3. **Test Coverage:** 100% of critical paths tested in staging
4. **False Positive Rate:** <5% for staging alerts
5. **Test Execution Time:** <15 minutes for full staging validation

## Rollout Plan

### Week 1: Foundation
- Implement GCP integration modules
- Set up authentication and secrets
- Create basic log reader

### Week 2: Docker Testing
- Implement Docker Compose manager
- Create local test suites
- Add health check validation

### Week 3: Staging Testing
- Build endpoint validators
- Implement performance tests
- Create E2E test orchestrator

### Week 4: Integration & Polish
- Integrate with CI/CD
- Add monitoring and alerting
- Document and train team

## Risk Mitigation

1. **Authentication Issues**
   - Store multiple key paths
   - Implement fallback authentication
   - Add clear error messages

2. **Network Flakiness**
   - Implement retry logic
   - Add timeout configurations
   - Use circuit breakers

3. **Test Data Consistency**
   - Use dedicated test accounts
   - Implement data cleanup
   - Version test data schemas

## Maintenance Plan

1. **Weekly Reviews**
   - Review test failures
   - Update error filters
   - Optimize slow tests

2. **Monthly Updates**
   - Update staging endpoints
   - Refresh test data
   - Review performance baselines

3. **Quarterly Audits**
   - Full test suite review
   - Update documentation
   - Performance optimization

## Conclusion

This unified testing platform will provide comprehensive validation from local development through staging deployment, significantly reducing production issues and improving development velocity. The integration with existing test infrastructure ensures minimal disruption while maximizing value delivery.