
## Example prompts for running tests with Claude Code

- USING UNIFIED TEST RUNNER: One at a time, step through each cypress test. spawn a new sub agent. upgrade the test to refect current SUT.
- USING UNIFIED TEST RUNNER: One at a time, step through each e2e test. spawn a new sub agent. Update test to reflect current claude.md standards and the SUT. Run the test. Fix the SUT. 
- USING UNIFIED TEST RUNNER: One at a time, step through each e2e test. spawn a new sub agent. Run the test. Fix the SUT.  MOST LIKELY TO FAIL first. 
- USING UNIFIED TEST RUNNER: One at a time, step through each integration test. spawn a new sub agent. Update test to reflect current claude.md standards and the SUT. Run the test. Fix the SUT. 
- USING UNIFIED TEST RUNNER: One at a time, step through each integration test, audit if the test is legacy or useful for active real system under test. Update it as needed or if it's of negative value add delete it.
- USING UNIFIED TEST RUNNER: One at a time, run all tests related to agents. spawn a new sub agent. Run the test. Fix the SUT. 
- USING UNIFIED TEST RUNNER: Run integration tests related to agents. spawn a new sub agent. Run the test. Fix the system under test for failures. focus on tests MOST LIKELY TO FAIL first. 
- USING UNIFIED TEST RUNNER: One at a time, step through each e2e real llm agent tests. spawn a new sub agent. Run the test. Fix the SUT.  MOST LIKELY TO FAIL first. 
- USING UNIFIED TEST RUNNER: One at a time, step through each cypress real llm agent tests. spawn a new sub agent. Run the test. Fix the SUT.  MOST LIKELY TO FAIL first. 
