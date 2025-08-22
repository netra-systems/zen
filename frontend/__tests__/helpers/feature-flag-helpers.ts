/**
 * Feature Flag Test Helpers
 * Convenience wrapper around test-utils/feature-flags for test directories
 */

import { 
  describeFeature, 
  itFeature, 
  isFeatureEnabled,
  shouldSkipFeature 
} from '../../test-utils/feature-flags';

/**
 * Conditional describe block based on feature flag
 * @param featureName - The feature flag name to check
 * @param suiteName - The test suite description
 * @param fn - The test suite function
 */
export const describeIfFeature = (
  featureName: string,
  suiteName: string,
  fn: () => void
): void => {
  describeFeature(featureName, suiteName, fn);
};

/**
 * Conditional it block based on feature flag
 * @param featureName - The feature flag name to check
 * @param testName - The test description
 * @param fn - The test function
 */
export const itIfFeature = (
  featureName: string,
  testName: string,
  fn: () => void | Promise<void>
): void => {
  itFeature(featureName, testName, fn);
};

// Re-export utilities for convenience
export { isFeatureEnabled, shouldSkipFeature };