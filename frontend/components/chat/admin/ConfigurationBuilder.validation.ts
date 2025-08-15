/**
 * Configuration Validation Utilities
 * 
 * Validation logic for corpus configuration.
 * Each function ≤8 lines for architectural compliance.
 */

import type { CorpusConfiguration, ValidationResult } from './ConfigurationBuilder.types';

// ≤8 lines: Main validation function
export const validateConfiguration = (config: CorpusConfiguration): ValidationResult => {
  const errors = collectValidationErrors(config);
  return { valid: errors.length === 0, errors };
};

// ≤8 lines: Collect all validation errors
export const collectValidationErrors = (config: CorpusConfiguration): string[] => {
  const errors: string[] = [];
  validateBasicFields(config, errors);
  validateWorkloadSelection(config, errors);
  validateRecordCount(config, errors);
  return errors;
};

// ≤8 lines: Validate basic fields
export const validateBasicFields = (config: CorpusConfiguration, errors: string[]): void => {
  if (!config.name || config.name.length < 3) {
    errors.push('Corpus name must be at least 3 characters');
  }
  if (!config.domain) {
    errors.push('Domain is required');
  }
};

// ≤8 lines: Validate workload selection
export const validateWorkloadSelection = (config: CorpusConfiguration, errors: string[]): void => {
  if (!config.workloadTypes.some(w => w.selected)) {
    errors.push('Select at least one workload type');
  }
};

// ≤8 lines: Validate record count
export const validateRecordCount = (config: CorpusConfiguration, errors: string[]): void => {
  const { recordCount } = config.parameters;
  if (recordCount < 100 || recordCount > 10000000) {
    errors.push('Record count must be between 100 and 10,000,000');
  }
};

// ≤8 lines: Check if configuration is valid
export const isConfigurationValid = (config: CorpusConfiguration): boolean => {
  const errors = collectValidationErrors(config);
  return errors.length === 0;
};