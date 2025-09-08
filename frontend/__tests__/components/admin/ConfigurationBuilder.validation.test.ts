/**
 * ConfigurationBuilder Validation Test Suite
 * 
 * Comprehensive tests for corpus configuration validation logic.
 * Tests all validation functions, edge cases, and error conditions.
 * Total: 15 meaningful tests focusing on validation behavior.
 */

import {
  validateConfiguration,
  collectValidationErrors,
  validateBasicFields,
  validateWorkloadSelection,
  validateRecordCount,
  isConfigurationValid
} from '../../../components/chat/admin/ConfigurationBuilder.validation';

import type { CorpusConfiguration } from '../../../components/chat/admin/ConfigurationBuilder.types';

describe('ConfigurationBuilder Validation', () => {
  // Test data fixtures
  const validConfiguration: CorpusConfiguration = {
    name: 'Valid Corpus Name',
    domain: 'ecommerce',
    workloadTypes: [
      { id: 'web', name: 'Web Requests', selected: true },
      { id: 'api', name: 'API Calls', selected: false }
    ],
    parameters: {
      recordCount: 1000,
      complexity: 'medium',
      errorRate: 0.01,
      distribution: 'normal',
      concurrency: 10
    },
    targetTable: 'test_table',
    optimizationFocus: 'balanced'
  };

  const invalidConfiguration: CorpusConfiguration = {
    name: '',
    domain: '',
    workloadTypes: [
      { id: 'web', name: 'Web Requests', selected: false },
      { id: 'api', name: 'API Calls', selected: false }
    ],
    parameters: {
      recordCount: 50,
      complexity: 'medium',
      errorRate: 0.01,
      distribution: 'normal',
      concurrency: 10
    },
    targetTable: '',
    optimizationFocus: 'balanced'
  };

  describe('validateConfiguration', () => {
    it('returns valid result for valid configuration', () => {
      const result = validateConfiguration(validConfiguration);
      
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('returns invalid result for invalid configuration', () => {
      const result = validateConfiguration(invalidConfiguration);
      
      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('includes all validation errors in result', () => {
      const result = validateConfiguration(invalidConfiguration);
      
      expect(result.errors).toContain('Corpus name must be at least 3 characters');
      expect(result.errors).toContain('Domain is required');
      expect(result.errors).toContain('Select at least one workload type');
      expect(result.errors).toContain('Record count must be between 100 and 10,000,000');
    });

    it('returns ValidationResult type with correct structure', () => {
      const result = validateConfiguration(validConfiguration);
      
      expect(result).toHaveProperty('valid');
      expect(result).toHaveProperty('errors');
      expect(typeof result.valid).toBe('boolean');
      expect(Array.isArray(result.errors)).toBe(true);
    });
  });

  describe('collectValidationErrors', () => {
    it('returns empty array for valid configuration', () => {
      const errors = collectValidationErrors(validConfiguration);
      expect(errors).toHaveLength(0);
    });

    it('returns all errors for invalid configuration', () => {
      const errors = collectValidationErrors(invalidConfiguration);
      expect(errors.length).toBeGreaterThan(0);
    });

    it('includes name validation errors', () => {
      const config = { ...validConfiguration, name: 'ab' };
      const errors = collectValidationErrors(config);
      
      expect(errors).toContain('Corpus name must be at least 3 characters');
    });

    it('includes domain validation errors', () => {
      const config = { ...validConfiguration, domain: '' };
      const errors = collectValidationErrors(config);
      
      expect(errors).toContain('Domain is required');
    });

    it('includes workload validation errors', () => {
      const config = {
        ...validConfiguration,
        workloadTypes: [
          { id: 'web', name: 'Web Requests', selected: false },
          { id: 'api', name: 'API Calls', selected: false }
        ]
      };
      const errors = collectValidationErrors(config);
      
      expect(errors).toContain('Select at least one workload type');
    });

    it('includes record count validation errors', () => {
      const config = {
        ...validConfiguration,
        parameters: { ...validConfiguration.parameters, recordCount: 50 }
      };
      const errors = collectValidationErrors(config);
      
      expect(errors).toContain('Record count must be between 100 and 10,000,000');
    });
  });

  describe('validateBasicFields', () => {
    it('adds error for empty name', () => {
      const errors: string[] = [];
      validateBasicFields({ ...validConfiguration, name: '' }, errors);
      
      expect(errors).toContain('Corpus name must be at least 3 characters');
    });

    it('adds error for short name', () => {
      const errors: string[] = [];
      validateBasicFields({ ...validConfiguration, name: 'ab' }, errors);
      
      expect(errors).toContain('Corpus name must be at least 3 characters');
    });

    it('does not add error for valid name', () => {
      const errors: string[] = [];
      validateBasicFields(validConfiguration, errors);
      
      expect(errors).not.toContain('Corpus name must be at least 3 characters');
    });

    it('adds error for empty domain', () => {
      const errors: string[] = [];
      validateBasicFields({ ...validConfiguration, domain: '' }, errors);
      
      expect(errors).toContain('Domain is required');
    });

    it('does not add error for valid domain', () => {
      const errors: string[] = [];
      validateBasicFields(validConfiguration, errors);
      
      expect(errors).not.toContain('Domain is required');
    });

    it('handles exactly 3 character name', () => {
      const errors: string[] = [];
      validateBasicFields({ ...validConfiguration, name: 'abc' }, errors);
      
      expect(errors).not.toContain('Corpus name must be at least 3 characters');
    });
  });

  describe('validateWorkloadSelection', () => {
    it('adds error when no workloads selected', () => {
      const errors: string[] = [];
      const config = {
        ...validConfiguration,
        workloadTypes: [
          { id: 'web', name: 'Web Requests', selected: false },
          { id: 'api', name: 'API Calls', selected: false }
        ]
      };
      
      validateWorkloadSelection(config, errors);
      expect(errors).toContain('Select at least one workload type');
    });

    it('does not add error when at least one workload selected', () => {
      const errors: string[] = [];
      validateWorkloadSelection(validConfiguration, errors);
      
      expect(errors).not.toContain('Select at least one workload type');
    });

    it('handles empty workload types array', () => {
      const errors: string[] = [];
      const config = { ...validConfiguration, workloadTypes: [] };
      
      validateWorkloadSelection(config, errors);
      expect(errors).toContain('Select at least one workload type');
    });

    it('handles multiple selected workloads', () => {
      const errors: string[] = [];
      const config = {
        ...validConfiguration,
        workloadTypes: [
          { id: 'web', name: 'Web Requests', selected: true },
          { id: 'api', name: 'API Calls', selected: true }
        ]
      };
      
      validateWorkloadSelection(config, errors);
      expect(errors).not.toContain('Select at least one workload type');
    });
  });

  describe('validateRecordCount', () => {
    it('adds error for record count below minimum', () => {
      const errors: string[] = [];
      const config = {
        ...validConfiguration,
        parameters: { ...validConfiguration.parameters, recordCount: 99 }
      };
      
      validateRecordCount(config, errors);
      expect(errors).toContain('Record count must be between 100 and 10,000,000');
    });

    it('adds error for record count above maximum', () => {
      const errors: string[] = [];
      const config = {
        ...validConfiguration,
        parameters: { ...validConfiguration.parameters, recordCount: 10000001 }
      };
      
      validateRecordCount(config, errors);
      expect(errors).toContain('Record count must be between 100 and 10,000,000');
    });

    it('does not add error for valid record count', () => {
      const errors: string[] = [];
      validateRecordCount(validConfiguration, errors);
      
      expect(errors).not.toContain('Record count must be between 100 and 10,000,000');
    });

    it('accepts minimum boundary value', () => {
      const errors: string[] = [];
      const config = {
        ...validConfiguration,
        parameters: { ...validConfiguration.parameters, recordCount: 100 }
      };
      
      validateRecordCount(config, errors);
      expect(errors).not.toContain('Record count must be between 100 and 10,000,000');
    });

    it('accepts maximum boundary value', () => {
      const errors: string[] = [];
      const config = {
        ...validConfiguration,
        parameters: { ...validConfiguration.parameters, recordCount: 10000000 }
      };
      
      validateRecordCount(config, errors);
      expect(errors).not.toContain('Record count must be between 100 and 10,000,000');
    });

    it('handles zero record count', () => {
      const errors: string[] = [];
      const config = {
        ...validConfiguration,
        parameters: { ...validConfiguration.parameters, recordCount: 0 }
      };
      
      validateRecordCount(config, errors);
      expect(errors).toContain('Record count must be between 100 and 10,000,000');
    });

    it('handles negative record count', () => {
      const errors: string[] = [];
      const config = {
        ...validConfiguration,
        parameters: { ...validConfiguration.parameters, recordCount: -100 }
      };
      
      validateRecordCount(config, errors);
      expect(errors).toContain('Record count must be between 100 and 10,000,000');
    });
  });

  describe('isConfigurationValid', () => {
    it('returns true for valid configuration', () => {
      const result = isConfigurationValid(validConfiguration);
      expect(result).toBe(true);
    });

    it('returns false for invalid configuration', () => {
      const result = isConfigurationValid(invalidConfiguration);
      expect(result).toBe(false);
    });

    it('returns false for configuration with any validation error', () => {
      const config = { ...validConfiguration, name: 'ab' };
      const result = isConfigurationValid(config);
      expect(result).toBe(false);
    });

    it('returns true only when all validations pass', () => {
      // Test multiple configurations
      const configs = [
        validConfiguration,
        { ...validConfiguration, name: 'ab' },
        { ...validConfiguration, domain: '' },
        { ...validConfiguration, parameters: { ...validConfiguration.parameters, recordCount: 50 } }
      ];
      
      const results = configs.map(isConfigurationValid);
      expect(results).toEqual([true, false, false, false]);
    });
  });
});