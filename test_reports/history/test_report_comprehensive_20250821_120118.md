# Netra AI Platform - Test Report

**Generated:** 2025-08-21T10:58:52.807364  
**Test Level:** comprehensive - Full test suite with coverage including staging tests (30-45 minutes)  

## 1. Test Summary

[FAILED] **OVERALL STATUS**

### Test Counts (Extracted from pytest output)
- **Total Tests:** 0
- **Passed:** 0 
- **Failed:** 0
- **Skipped:** 0
- **Errors:** 0

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 0 | 0 | 0 | 0 | 0 | 4.48s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.93s | [FAILED] |

## 3. Environment and Configuration

- **Test Level:** comprehensive
- **Description:** Full test suite with coverage including staging tests (30-45 minutes)
- **Purpose:** Pre-release validation, full system testing including staging environment
- **Timeout:** 2700s
- **Coverage Enabled:** Yes
- **Total Duration:** 5.41s
- **Exit Code:** 15

### Backend Configuration
```
netra_backend/tests tests integration_tests --coverage --parallel=6 --html-output --fail-fast
```

### Frontend Configuration
```
--coverage
```

## 4. Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: all
  Parallel: 6
  Coverage: disabled
  Fail Fast: enabled
  Environment: test

Running command:
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini netra_backend/tests tests integration_tests -v -n 6 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings --html=reports/tests/report.html --self-contained-html
================================================================================
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 3.80s

[Report] HTML Report: reports/tests/report.html
================================================================================

ImportError while loading conftest 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\conftest.py'.
netra_backend\tests\conftest.py:59: in <module>
    from netra_backend.app.routes.mcp.main import app
netra_backend\app\routes\mcp\__init__.py:8: in <module>
    from netra_backend.app.routes.mcp.main import router
netra_backend\app\routes\mcp\main.py:13: in <module>
    from netra_backend.app.auth_integration.auth import get_current_user, get_current_user_optional
netra_backend\app\auth_integration\__init__.py:87: in <module>
    from netra_backend.app.services.synthetic_data.validators import (
netra_backend\app\services\synthetic_data\__init__.py:5: in <module>
    from netra_backend.app.services.synthetic_data.core_service import SyntheticDataService, synthetic_data_service
netra_backend\app\services\synthetic_data\core_service.py:9: in <module>
    from netra_backend.app.services.synthetic_data.synthetic_data_service_main import SyntheticDataService, synthetic_data_service
netra_backend\app\services\synthetic_data\synthetic_data_service_main.py:7: in <module>
    from netra_backend.app.services.synthetic_data.generation_coordinator import GenerationCoordinator
netra_backend\app\services\synthetic_data\generation_coordinator.py:8: in <module>
    from netra_backend.app.services.synthetic_data.core_service_base import CoreServiceBase
netra_backend\app\services\synthetic_data\core_service_base.py:13: in <module>
    from netra_backend.app.services.synthetic_data.job_manager import JobManager
netra_backend\app\services\synthetic_data\job_manager.py:15: in <module>
    from netra_backend.app.services.quality_monitoring.metrics import calculate_generation_rate
netra_backend\app\services\quality_monitoring\__init__.py:3: in <module>
    from netra_backend.app.services.quality_monitoring.service import QualityMonitoringService
netra_backend\app\services\quality_monitoring\service.py:17: in <module>
    from netra_backend.app.services.quality_monitoring.analytics import TrendAnalyzer
netra_backend\app\services\quality_monitoring\analytics.py:10: in <module>
    from netra_backend.app.services.apex_optimizer_agent.models import QualityTrend, MetricType, AgentQualityProfile
E   ImportError: cannot import name 'QualityTrend' from 'netra_backend.app.services.apex_optimizer_agent.models' (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\services\apex_optimizer_agent\models.py)

```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> node run-jest.js --config jest.config.simple.cjs --forceExit --detectOpenHandles --coverage --coverageDirectory=../reports/frontend-coverage


Error: Can't find a root directory while resolving a config file path.
Provided path to resolve: jest.config.simple.cjs
cwd: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend
    at resolveConfigPath (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend\node_modules\jest-config\build\index.js:2448:11)
    at readInitialOptions (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend\node_modules\jest-config\build\index.js:1138:55)
    at readConfig (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend\node_modules\jest-config\build\index.js:918:13)
    at readConfigs (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend\node_modules\jest-config\build\index.js:1168:32)
    at runCLI (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend\node_modules\@jest\core\build\index.js:1393:43)
    at Object.run (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend\node_modules\jest-cli\build\index.js:656:34)

```

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
