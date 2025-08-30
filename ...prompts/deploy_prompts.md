CRITICAL: This is of the highest importance:

Each time using a subagent ONE AT A TIME to execute the each part of the work: 
A:1: New sub agent: Validate staging config, reading recent learnings etc. for issues. Re-deploy each existing service (fresh build) to staging
A:2: New sub agent: Audit GCP staging logs for all issues, both literal errors and log statements that show issues
 Use “Five whys” (5 whys) method to analyze and drill down to root cause. Most errors are not what they first seem, e.g. config errors, regression, context specific, missing or bad config, config exists but not passed, duplicates, regressions etc.
A:3: New sub agent: Create a failing test that replicates the issue. Then think about one or two similar cases and create another failing test.   Log learnings to prevent regressions.
A:4: New sub agent: Fix issues and pass test by fixing real system. Log learnings to prevent regressions.

REPEAT A until all services are healthy or 30 times

AFTER everything seems to be working
Each time using a subagent ONE AT A TIME to execute the work: 
B:1: New sub agent: Run tests directly on staging env
B:2: New sub agent: Fix issues

REPEAT B until all services are healthy or 30 times
