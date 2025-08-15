/**
 * Configuration Data Utilities
 * 
 * Data initialization and management for corpus configuration.
 * Each function ≤8 lines for architectural compliance.
 */

import type {
  WorkloadType,
  GenerationParams,
  CorpusConfiguration,
  ComplexityLevel,
  DistributionType
} from './ConfigurationBuilder.types';

// ≤8 lines: Initialize workload types
export const initializeWorkloadTypes = (): WorkloadType[] => {
  const workloads: WorkloadType[] = [
    { id: 'data_processing', name: 'Data Processing', selected: false },
    { id: 'machine_learning', name: 'Machine Learning', selected: false },
    { id: 'web_services', name: 'Web Services', selected: false },
    { id: 'database', name: 'Database', selected: false },
    { id: 'analytics', name: 'Analytics', selected: false },
    { id: 'infrastructure', name: 'Infrastructure', selected: false }
  ];
  return workloads;
};

// ≤8 lines: Initialize generation parameters
export const initializeGenerationParams = (): GenerationParams => {
  return {
    recordCount: 10000,
    complexity: 'medium' as ComplexityLevel,
    errorRate: 0.01,
    distribution: 'normal' as DistributionType,
    concurrency: 10
  };
};

// ≤8 lines: Initialize complete configuration
export const initializeConfiguration = (): CorpusConfiguration => {
  return {
    name: '',
    domain: '',
    workloadTypes: initializeWorkloadTypes(),
    parameters: initializeGenerationParams(),
    targetTable: '',
    optimizationFocus: 'balanced'
  };
};

// ≤8 lines: Get selected workload types
export const getSelectedWorkloadTypes = (workloadTypes: WorkloadType[]): WorkloadType[] => {
  return workloadTypes.filter(w => w.selected);
};

// ≤8 lines: Get selected workload IDs
export const getSelectedWorkloadIds = (workloadTypes: WorkloadType[]): string[] => {
  return workloadTypes.filter(w => w.selected).map(w => w.id);
};