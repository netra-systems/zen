/**
 * Authentication Integration Test
 * Quick verification that all auth components work together
 */

import { unifiedAuthService, authInterceptor } from '@/lib/unified-auth-service';
import { logger } from '@/lib/logger';

interface TestResult {
  test: string;
  passed: boolean;
  error?: string;
}

/**
 * Test the authentication integration
 */
export async function testAuthIntegration(): Promise<TestResult[]> {
  const results: TestResult[] = [];

  // Test 1: Unified auth service initialization
  try {
    const authResult = await unifiedAuthService.initialize();
    results.push({
      test: 'Unified Auth Service Initialization',
      passed: authResult.valid || authResult.error === 'No token found',
      error: authResult.error
    });
  } catch (error) {
    results.push({
      test: 'Unified Auth Service Initialization',
      passed: false,
      error: (error as Error).message
    });
  }

  // Test 2: Auth interceptor functionality
  try {
    // Test with a safe endpoint that should work
    const response = await authInterceptor.authenticatedFetch('/api/health', {
      skipAuth: true // Skip auth for health check
    });
    results.push({
      test: 'Auth Interceptor Basic Functionality',
      passed: true
    });
  } catch (error) {
    results.push({
      test: 'Auth Interceptor Basic Functionality',
      passed: false,
      error: (error as Error).message
    });
  }

  // Test 3: Auth configuration retrieval
  try {
    const config = await unifiedAuthService.getAuthConfig();
    results.push({
      test: 'Auth Configuration Retrieval',
      passed: !!config && !!config.endpoints,
      error: !config ? 'No config returned' : undefined
    });
  } catch (error) {
    results.push({
      test: 'Auth Configuration Retrieval',
      passed: false,
      error: (error as Error).message
    });
  }

  // Test 4: WebSocket auth config
  try {
    const wsConfig = unifiedAuthService.getWebSocketAuthConfig();
    results.push({
      test: 'WebSocket Auth Configuration',
      passed: !!wsConfig && typeof wsConfig.refreshToken === 'function',
      error: !wsConfig ? 'No WebSocket config returned' : undefined
    });
  } catch (error) {
    results.push({
      test: 'WebSocket Auth Configuration',
      passed: false,
      error: (error as Error).message
    });
  }

  // Test 5: Auth headers generation
  try {
    const headers = unifiedAuthService.getAuthHeaders();
    results.push({
      test: 'Auth Headers Generation',
      passed: typeof headers === 'object',
      error: typeof headers !== 'object' ? 'Headers not returned as object' : undefined
    });
  } catch (error) {
    results.push({
      test: 'Auth Headers Generation',
      passed: false,
      error: (error as Error).message
    });
  }

  return results;
}

/**
 * Log test results in a readable format
 */
export function logTestResults(results: TestResult[]): void {
  const passed = results.filter(r => r.passed).length;
  const total = results.length;
  
  logger.info(`Auth Integration Test Results: ${passed}/${total} tests passed`, {
    component: 'AuthIntegrationTest',
    results: results.map(r => ({
      test: r.test,
      status: r.passed ? 'PASS' : 'FAIL',
      error: r.error
    }))
  });

  console.group('🔐 Auth Integration Test Results');
  console.log(`✅ ${passed}/${total} tests passed\n`);
  
  results.forEach(result => {
    const icon = result.passed ? '✅' : '❌';
    const status = result.passed ? 'PASS' : 'FAIL';
    console.log(`${icon} ${result.test}: ${status}`);
    if (result.error) {
      console.log(`   Error: ${result.error}`);
    }
  });
  
  console.groupEnd();
}

/**
 * Run the complete authentication test suite
 */
export async function runAuthTests(): Promise<boolean> {
  logger.info('Starting authentication integration tests');
  
  try {
    const results = await testAuthIntegration();
    logTestResults(results);
    
    const allPassed = results.every(r => r.passed);
    
    if (allPassed) {
      logger.info('All authentication tests passed');
    } else {
      logger.warn('Some authentication tests failed');
    }
    
    return allPassed;
  } catch (error) {
    logger.error('Auth tests failed to run', error as Error);
    return false;
  }
}

// Export for use in development/debugging
if (typeof window !== 'undefined') {
  (window as any).testAuth = runAuthTests;
}