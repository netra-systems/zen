/**
 * Feature flag helpers for Jest tests
 * 
 * Enables conditional test execution based on feature flags,
 * supporting TDD workflow and 100% pass rate for enabled features.
 * 
 * @compliance conventions.xml - Max 8 lines per function
 */

import * as fs from 'fs';
import * as path from 'path';

// Feature status enum matching Python implementation
export enum FeatureStatus {
  ENABLED = 'enabled',
  IN_DEVELOPMENT = 'in_development',
  DISABLED = 'disabled',
  EXPERIMENTAL = 'experimental'
}

// Feature flag configuration interface
export interface FeatureFlag {
  status: FeatureStatus;
  description: string;
  owner?: string;
  target_release?: string;
  dependencies?: string[];
  metadata?: Record<string, any>;
}

// Load feature flags from config file
const loadFeatureFlags = (): Record<string, FeatureFlag> => {
  const configPath = path.join(__dirname, '..', '..', '..', 'test_feature_flags.json');
  if (!fs.existsSync(configPath)) {
    return {};
  }
  const data = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  return data.features || {};
};

// Check environment variable overrides
const getEnvOverride = (featureName: string): FeatureStatus | null => {
  const envKey = `TEST_FEATURE_${featureName.toUpperCase()}`;
  const envValue = process.env[envKey];
  if (envValue && Object.values(FeatureStatus).includes(envValue as FeatureStatus)) {
    return envValue as FeatureStatus;
  }
  return null;
};

// Check if a feature is enabled
export const isFeatureEnabled = (featureName: string): boolean => {
  const flags = loadFeatureFlags();
  const envOverride = getEnvOverride(featureName);
  const status = envOverride || flags[featureName]?.status || FeatureStatus.ENABLED;
  return status === FeatureStatus.ENABLED;
};

// Check if tests should be skipped for a feature
export const shouldSkipFeature = (featureName: string): boolean => {
  const flags = loadFeatureFlags();
  const envOverride = getEnvOverride(featureName);
  const status = envOverride || flags[featureName]?.status || FeatureStatus.ENABLED;
  return status === FeatureStatus.IN_DEVELOPMENT || status === FeatureStatus.DISABLED;
};

// Get skip reason for a feature
export const getSkipReason = (featureName: string): string => {
  const flags = loadFeatureFlags();
  const flag = flags[featureName];
  if (!flag) return '';
  
  switch (flag.status) {
    case FeatureStatus.IN_DEVELOPMENT:
      return `Feature '${featureName}' is in development${flag.target_release ? ` (target: ${flag.target_release})` : ''}`;
    case FeatureStatus.DISABLED:
      return `Feature '${featureName}' is disabled`;
    case FeatureStatus.EXPERIMENTAL:
      return `Feature '${featureName}' is experimental`;
    default:
      return '';
  }
};

/**
 * Skip test suite if feature is not enabled
 * Usage: describeIfFeature('feature_name', 'Test Suite Name', () => { ... })
 */
export const describeIfFeature = (
  featureName: string,
  suiteName: string,
  fn: jest.EmptyFunction
): void => {
  if (shouldSkipFeature(featureName)) {
    describe.skip(`${suiteName} [${getSkipReason(featureName)}]`, fn);
  } else {
    describe(suiteName, fn);
  }
};

/**
 * Skip individual test if feature is not enabled
 * Usage: itIfFeature('feature_name', 'should do something', () => { ... })
 */
export const itIfFeature = (
  featureName: string,
  testName: string,
  fn?: jest.ProvidesCallback
): void => {
  if (shouldSkipFeature(featureName)) {
    it.skip(`${testName} [${getSkipReason(featureName)}]`, fn || (() => {}));
  } else {
    it(testName, fn);
  }
};

/**
 * Skip test if feature is experimental (optional tests)
 */
export const itIfNotExperimental = (
  featureName: string,
  testName: string,
  fn?: jest.ProvidesCallback
): void => {
  const flags = loadFeatureFlags();
  const flag = flags[featureName];
  if (flag?.status === FeatureStatus.EXPERIMENTAL) {
    it.skip(`${testName} [Feature is experimental]`, fn || (() => {}));
  } else {
    it(testName, fn);
  }
};

/**
 * Mark test as pending for in-development features
 * Shows in test output but doesn't fail the suite
 */
export const pendingIfInDevelopment = (
  featureName: string,
  testName: string,
  fn?: jest.ProvidesCallback
): void => {
  const flags = loadFeatureFlags();
  const flag = flags[featureName];
  if (flag?.status === FeatureStatus.IN_DEVELOPMENT) {
    it.todo(`${testName} [In Development]`);
  } else {
    it(testName, fn);
  }
};

/**
 * Get all enabled features for reporting
 */
export const getEnabledFeatures = (): string[] => {
  const flags = loadFeatureFlags();
  return Object.entries(flags)
    .filter(([_, flag]) => flag.status === FeatureStatus.ENABLED)
    .map(([name, _]) => name);
};

/**
 * Get all in-development features for reporting
 */
export const getInDevelopmentFeatures = (): string[] => {
  const flags = loadFeatureFlags();
  return Object.entries(flags)
    .filter(([_, flag]) => flag.status === FeatureStatus.IN_DEVELOPMENT)
    .map(([name, _]) => name);
};

/**
 * Log feature flag status for debugging
 */
export const logFeatureStatus = (featureName: string): void => {
  const flags = loadFeatureFlags();
  const flag = flags[featureName];
  const envOverride = getEnvOverride(featureName);
  
  console.log(`Feature: ${featureName}`);
  console.log(`  Status: ${flag?.status || 'not configured (defaults to enabled)'}`);
  if (envOverride) {
    console.log(`  Environment Override: ${envOverride}`);
  }
  if (flag?.owner) {
    console.log(`  Owner: ${flag.owner}`);
  }
  if (flag?.target_release) {
    console.log(`  Target Release: ${flag.target_release}`);
  }
};

// Export feature status enum for use in tests
export { FeatureStatus };