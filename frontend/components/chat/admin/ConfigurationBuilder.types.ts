/**
 * ConfigurationBuilder Types
 * 
 * Strong TypeScript typing for corpus configuration.
 * Single source of truth for all configuration-related types.
 */

// Core type definitions
export type ComplexityLevel = 'low' | 'medium' | 'high';
export type DistributionType = 'normal' | 'uniform' | 'exponential';
export type OptimizationFocus = 'performance' | 'quality' | 'balanced';
export type DomainType = 'ecommerce' | 'fintech' | 'healthcare' | 'saas' | 'iot';

// Workload type definition
export interface WorkloadType {
  readonly id: string;
  readonly name: string;
  selected: boolean;
}

// Generation parameters
export interface GenerationParams {
  recordCount: number;
  complexity: ComplexityLevel;
  errorRate: number;
  distribution: DistributionType;
  concurrency: number;
}

// Validation result
export interface ValidationResult {
  readonly valid: boolean;
  readonly errors: readonly string[];
}

// Main configuration interface
export interface CorpusConfiguration {
  name: string;
  domain: DomainType | '';
  workloadTypes: WorkloadType[];
  parameters: GenerationParams;
  targetTable: string;
  optimizationFocus: OptimizationFocus;
}

// Component props
export interface ConfigurationBuilderProps {
  onConfigurationComplete: (config: CorpusConfiguration) => void;
  sessionId: string;
  className?: string;
}

// WebSocket message types
export interface ConfigSuggestionRequest {
  message_type: 'config_suggestion_request';
  optimization_focus: OptimizationFocus;
  domain: DomainType | '';
  workload_type?: string;
  session_id: string;
}

export interface CorpusGenerationRequest {
  message_type: 'corpus_generation_request';
  domain: DomainType | '';
  workload_types: string[];
  parameters: GenerationParams;
  target_table: string;
  session_id: string;
}