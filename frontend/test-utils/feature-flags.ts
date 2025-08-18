/**
 * Feature Flag Utilities for Frontend Tests
 * ==========================================
 * 
 * Provides feature flag support for Jest tests to enable TDD workflow
 * while maintaining 100% pass rate for enabled features.
 */

import { describe as jestDescribe, it as jestIt, test as jestTest } from '@jest/globals';

// Feature flag configuration
interface FeatureConfig {
  status: 'enabled' | 'in_development' | 'disabled' | 'experimental';
  description?: string;
}

// Load feature flags from environment or config
const loadFeatureFlags = (): Record<string, FeatureConfig> => {
  // In production, this would load from test_feature_flags.json
  // For now, we'll use a simple mapping
  return {
    'roi_calculator': { status: 'in_development', description: 'ROI Calculator feature' },
    'first_time_user_flow': { status: 'in_development', description: 'First-time user onboarding' },
    'auth_integration': { status: 'enabled', description: 'Authentication integration' },
    'websocket_streaming': { status: 'enabled', description: 'WebSocket streaming' },
    'github_integration': { status: 'in_development', description: 'GitHub integration' },
  };
};

const FEATURE_FLAGS = loadFeatureFlags();

/**
 * Check if a feature is enabled
 */
export const isFeatureEnabled = (featureName: string): boolean => {
  const flag = FEATURE_FLAGS[featureName];
  return flag?.status === 'enabled';
};

/**
 * Check if a feature should skip tests
 */
export const shouldSkipFeature = (featureName: string): boolean => {
  const flag = FEATURE_FLAGS[featureName];
  return flag?.status === 'in_development' || flag?.status === 'disabled';
};

/**
 * Feature-flagged describe block
 * Skips entire test suite if feature is not enabled
 */
export const describeFeature = (
  featureName: string,
  name: string,
  fn: () => void
): void => {
  if (shouldSkipFeature(featureName)) {
    jestDescribe.skip(`[${featureName}] ${name}`, fn);
  } else {
    jestDescribe(name, fn);
  }
};

/**
 * Feature-flagged test
 * Skips test if feature is not enabled
 */
export const testFeature = (
  featureName: string,
  name: string,
  fn: () => void | Promise<void>
): void => {
  if (shouldSkipFeature(featureName)) {
    jestTest.skip(`[${featureName}] ${name}`, fn);
  } else {
    jestTest(name, fn);
  }
};

/**
 * Feature-flagged it block
 * Skips test if feature is not enabled
 */
export const itFeature = (
  featureName: string,
  name: string,
  fn: () => void | Promise<void>
): void => {
  if (shouldSkipFeature(featureName)) {
    jestIt.skip(`[${featureName}] ${name}`, fn);
  } else {
    jestIt(name, fn);
  }
};

/**
 * TDD test that's expected to fail initially
 */
export const testTDD = (
  featureName: string,
  name: string,
  fn: () => void | Promise<void>
): void => {
  const flag = FEATURE_FLAGS[featureName];
  
  if (flag?.status === 'in_development') {
    // Mark as todo for TDD tests
    jestTest.todo(`[TDD: ${featureName}] ${name}`);
  } else if (flag?.status === 'disabled') {
    jestTest.skip(`[Disabled: ${featureName}] ${name}`, fn);
  } else {
    jestTest(name, fn);
  }
};

/**
 * Experimental test that only runs when opted in
 */
export const testExperimental = (
  name: string,
  fn: () => void | Promise<void>
): void => {
  if (process.env.ENABLE_EXPERIMENTAL_TESTS !== 'true') {
    jestTest.skip(`[Experimental] ${name}`, fn);
  } else {
    jestTest(name, fn);
  }
};

/**
 * Performance test with threshold
 */
export const testPerformance = (
  name: string,
  thresholdMs: number,
  fn: () => void | Promise<void>
): void => {
  jestTest(name, async () => {
    const start = Date.now();
    await fn();
    const duration = Date.now() - start;
    
    if (duration > thresholdMs) {
      throw new Error(`Performance threshold exceeded: ${duration}ms > ${thresholdMs}ms`);
    }
  });
};

/**
 * Test that requires multiple features
 */
export const testRequiresFeatures = (
  features: string[],
  name: string,
  fn: () => void | Promise<void>
): void => {
  const disabledFeatures = features.filter(f => !isFeatureEnabled(f));
  
  if (disabledFeatures.length > 0) {
    jestTest.skip(
      `[Requires: ${disabledFeatures.join(', ')}] ${name}`,
      fn
    );
  } else {
    jestTest(name, fn);
  }
};

// Re-export standard Jest functions for convenience
export { describe, it, test, expect, beforeEach, afterEach, beforeAll, afterAll } from '@jest/globals';