Phase 1: Stop the Bleeding (Week 1)
  1. Create browser environment test runner using Playwright/Puppeteer
  2. Add specific tests for WebSocket logger errors in browser context
  3. Fix the immediate runtime error (see solution below)

  Phase 2: Selective Unmocking (Week 2-4)
  1. Start with critical paths: WebSocket, Auth, Logger
  2. Fix API signature mismatches one service at a time
  3. Keep error suppression for non-critical errors initially

  Phase 3: Full Integration (Month 2)
  1. Remove error suppression completely
  2. Implement "Real Services by Default" policy
  3. Add production parity test environment
