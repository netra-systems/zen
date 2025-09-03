
## Example prompts for running tests with Claude Code



- USING UNIFIED TEST RUNNER (Docker test env): Run E2E tests with fast fail. spawn a new sub agent. Run the test. Fix the System under test. 

USING UNIFIED TEST RUNNER (Docker test env): Run critical tests with fast fail. spawn a new sub agent. Run the test. Fix the System under test.

USING UNIFIED TEST RUNNER (Docker test env): Run real LLM tests with fast fail. spawn a new sub agent. Run the test. Fix the System under test.


- USING UNIFIED TEST RUNNER: One at a time, step through each cypress test. spawn a new sub agent. upgrade the test to refect current SUT.
- USING UNIFIED TEST RUNNER: One at a time, step through each e2e test. spawn a new sub agent. Update test to reflect current claude.md standards and the SUT. Run the test. Fix the SUT. 
- USING UNIFIED TEST RUNNER: One at a time, step through each e2e test. spawn a new sub agent. Run the test. Fix the SUT.  MOST LIKELY TO FAIL first. 
- USING UNIFIED TEST RUNNER: One at a time, step through each integration test. spawn a new sub agent. Update test to reflect current claude.md standards and the SUT. Run the test. Fix the SUT. 
- USING UNIFIED TEST RUNNER: One at a time, step through each integration test, audit if the test is legacy or useful for active real system under test. Update it as needed or if it's of negative value add delete it.
- USING UNIFIED TEST RUNNER: One at a time, run all tests related to agents. spawn a new sub agent. Run the test. Fix the SUT. 
- USING UNIFIED TEST RUNNER: Run integration tests related to agents. spawn a new sub agent. Run the test. Fix the system under test for failures. focus on tests MOST LIKELY TO FAIL first. 
- USING UNIFIED TEST RUNNER: One at a time, step through each e2e real llm agent tests. spawn a new sub agent. Run the test. Fix the SUT.  MOST LIKELY TO FAIL first. 
- USING UNIFIED TEST RUNNER: Docker test env: One at a time, step through each cypress real llm agent tests. spawn a new sub agent. Run the test. Fix the SUT.  MOST LIKELY TO FAIL first. 

USING UNIFIED TEST RUNNER: Docker test env: Run "critical" tests. For each failure: spawn a new sub agent. Fix the SUT. Repeat until all tests pass or 100 times.

USING UNIFIED TEST RUNNER: Docker test env: Run "chat is king" tests. For each failure: spawn a new sub agent. Fix the SUT. Repeat until all tests pass or 100 times.


- USING UNIFIED TEST RUNNER: Using the "netra-dev" docker env. One at a time, step through each e2e REAL llm agent tests. spawn a new sub agent. Run the test. Fix the SUT.  MOST LIKELY TO FAIL first. 
 Fix all errors

 USING UNIFIED TEST RUNNER: Using the netra test docker env. One at a time, step through each e2e REAL llm agent tests. spawn a new sub agent. Run the test. Fix the SUT.  MOST LIKELY TO FAIL first. 

- USING UNIFIED TEST RUNNER: One at a time, for each step: spawn a new sub agent. run frontend tests -fast-fail (and think MOST LIKELY TO FAIL first). Fix the SUT.  
REPEAT each step at least 100 times or still all tests pass.

- USING UNIFIED TEST RUNNER: One at a time, for each step: spawn a new sub agent. run dev-env dev auto login and auth tests -fast-fail (and think MOST LIKELY TO FAIL first). Fix the SUT.  
REPEAT each step at least 100 times or still all tests pass.

 - USING UNIFIED TEST RUNNER: Run tests most likely to fail and fail the fastest first.  One at a time, step through each failure. spawn a new sub agent. Run the test. Fix the SUT. 
 - USING UNIFIED TEST RUNNER: Run AUTH tests most likely to fail and fail the fastest first.  One at a time, step through each failure. spawn a new sub agent. Run the test. Fix the SUT. 


 CRITICAL: Action and remediate each item in E2E_REAL_LLM_AUDIT_REPORT.md
for each item, one at a time, spawn a new sub agent team
do not bulk edit files, do one file at a time, run the tests , fix system under test

#1 USING UNIFIED TEST RUNNER: TODO List track all tests in e2e\frontend\FRONTEND_TEST_COVERAGE_REPORT.md  STEP: One at a time: spawn a new sub agent: run the test and fix the system under test
REPEAT each STEP at least 100 times or untill all tests pass.

# 2
USING UNIFIED TEST RUNNER:  STEP: Run tests most likely to fail and fail the fastest first.  One at a time, step  through each failure. spawn a new sub agent. Run the test. Fix the SUT.
  REPEAT each STEP at least 100 times or untill all tests pass.


  USING UNIFIED TEST RUNNER: Run REGRESSION tests most likely to fail and fail the fastest first.  One at a time, step through each failure. spawn a new sub agent. Run the test. Fix the SUT. 

    USING UNIFIED TEST RUNNER: If needed launch docker test (compose). Run unit and integration tests most likely to fail and fail the fastest first.  One at a time, step through each failure. spawn a new sub agent. Run the test. Fix the SUT. 

    
    USING UNIFIED TEST RUNNER with DOCKER COMPOSE DEDICATED TEST ENV: Run most likely to fail and fail the fastest first AND be the most useful. Use test discovery. One at a time, step through each failure. spawn a new sub agent. Run the test. Fix the SUT. 

    AUDIT e2e tests most badly using mocks One at a time, step through each failure. spawn a new sub agent. Make the test more realistic and much tougher. Focus on the BASICS, the most expected critical paths. Run it. Fix the system under test.

   the POINT of the staging test is to run the test items with the STAGING SERVICES DIRECTLY e.g. make API and WS     │
│   calls etc. the OAUTH SIMULATION should ONLY Be to mimic google oauth. make a plan to update this. must be able to run   │
│   e2e testing concept against the ALREADY DEPLOYED staging env.


 USING UNIFIED TEST RUNNER with DOCKER COMPOSE DEDICATED TEST ENV: Run most likely to fail and fail the fastest first AND be the most useful. Use test discovery. One at a time, step through each failure. spawn a new sub agent. Run the test. Fix the SUT. 
 
  USING UNIFIED TEST RUNNER with DOCKER COMPOSE DEDICATED TEST ENV: Run E2e agent tests most likely to fail and fail the fastest first AND be the most useful. Use test discovery. One at a time, step through each failure. spawn a new sub agent. Run the test. Fix the SUT. 