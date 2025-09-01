AUDIT AND remediate this.  DOCKER_CRASH_AUDIT_REPORT.md. In the context of 1) recent new scripts for cleaning      │
│   docker. 2) test should follow same as dev and use the "production" docker images because they reduce memory etc    │
│   3) MOST IMPORTANT: Solve the restart STORM while testing. A user must be able to spin up 10 unified test runner    │
│   things and they don't conflict. 4) CENTRALIZE all unified test runner logic related to handling docker this must   │
│   be a single unified class. Use a central file or env or something to mark and lock when one is starting up or      │
│   restarting test env . AND provide option to use this "shared" test env or create a new dedicated one. Asssume the  │
│   memory thing is not a problem the hardware is there the issue is the software abusing API calls to a single        │
│   named thing instead of properly managing parallel testing. yes orchestrator may solve in future but unified test   │
│   should still work. Remember: first do no harm second unify and coorindate.   