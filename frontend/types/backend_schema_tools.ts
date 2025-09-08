/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

import { ToolStatus } from './backend_schema_base';

// Tool-related interfaces
export interface ToolInput {
  tool_name: string;
  args?: unknown[];
  kwargs?: {
    [k: string]: unknown;
  };
}

export interface ToolResult {
  tool_input: ToolInput;
  status?: ToolStatus;
  message?: string;
  payload?: unknown;
  start_time?: number;
  end_time?: number | null;
}

export interface ToolInvocation {
  tool_result: ToolResult;
}

export interface ToolCompleted {
  tool_name: string;
  result: unknown;
}

export interface ToolStarted {
  tool_name: string;
}

// Content and corpus management
export interface ContentCorpus {
  record_id: string;
  workload_type: string;
  prompt: string;
  response: string;
  created_at: string;
  [k: string]: unknown;
}

export interface ContentCorpusGenParams {
  /**
   * Number of samples to generate for each workload type.
   */
  samples_per_type?: number;
  /**
   * Controls randomness. Higher is more creative.
   */
  temperature?: number;
  /**
   * Nucleus sampling probability.
   */
  top_p?: number | null;
  /**
   * Top-k sampling control.
   */
  top_k?: number | null;
  /**
   * Max CPU cores to use.
   */
  max_cores?: number;
  /**
   * The name of the ClickHouse table to store the corpus in.
   */
  clickhouse_table?: string;
}

export interface ContentGenParams {
  /**
   * Number of samples to generate for each workload type.
   */
  samples_per_type?: number;
  /**
   * Controls randomness. Higher is more creative.
   */
  temperature?: number;
  /**
   * Nucleus sampling probability.
   */
  top_p?: number | null;
  /**
   * Top-k sampling control.
   */
  top_k?: number | null;
  /**
   * Max CPU cores to use.
   */
  max_cores?: number;
}

export interface Corpus {
  name: string;
  description?: string | null;
  id: string;
  status: string;
  created_by_id: string;
  created_at: string;
  updated_at: string;
  [k: string]: unknown;
}

export interface CorpusBase {
  name: string;
  description?: string | null;
}

export interface CorpusCreate {
  name: string;
  description?: string | null;
}

export interface CorpusInDBBase {
  name: string;
  description?: string | null;
  id: string;
  status: string;
  created_by_id: string;
  created_at: string;
  updated_at: string;
  [k: string]: unknown;
}

export interface CorpusUpdate {
  name: string;
  description?: string | null;
}

// Supply option management
export interface SupplyOption {
  name: string;
  description?: string | null;
  id: number;
  [k: string]: unknown;
}

export interface SupplyOptionBase {
  name: string;
  description?: string | null;
}

export interface SupplyOptionCreate {
  name: string;
  description?: string | null;
}

export interface SupplyOptionInDB {
  name: string;
  description?: string | null;
  id: number;
  [k: string]: unknown;
}

export interface SupplyOptionInDBBase {
  name: string;
  description?: string | null;
  id: number;
  [k: string]: unknown;
}

export interface SupplyOptionUpdate {
  name: string;
  description?: string | null;
}

// Data generation and ingestion
export interface DataIngestionParams {
  /**
   * The path to the data file to ingest.
   */
  data_path: string;
  /**
   * The name of the table to ingest the data into.
   */
  table_name: string;
}

export interface LogGenParams {
  /**
   * The ID of the content corpus to use for generation.
   */
  corpus_id: string;
  /**
   * Number of log entries to generate.
   */
  num_logs?: number;
  /**
   * Max CPU cores to use.
   */
  max_cores?: number;
}

export interface SyntheticDataGenParams {
  /**
   * Number of traces to generate.
   */
  num_traces?: number;
  /**
   * Number of unique users to simulate.
   */
  num_users?: number;
  /**
   * The fraction of traces that should be errors.
   */
  error_rate?: number;
  /**
   * A list of event types to simulate.
   */
  event_types?: string[];
  /**
   * The name of the source ClickHouse table for the content corpus.
   */
  source_table?: string;
  /**
   * The name of the destination ClickHouse table for the generated data.
   */
  destination_table?: string;
}

// Pattern and policy management
export interface DiscoveredPattern {
  /**
   * The ID of the pattern.
   */
  pattern_id: string;
  /**
   * A description of the pattern.
   */
  description: string;
}

export interface LearnedPolicy {
  /**
   * The name of the pattern.
   */
  pattern_name: string;
  /**
   * The name of the optimal supply option.
   */
  optimal_supply_option_name: string;
}

export interface PredictedOutcome {
  /**
   * The name of the supply option.
   */
  supply_option_name: string;
  /**
   * The explanation of the outcome.
   */
  explanation: string;
}

// Reference management
export interface ReferenceCreateRequest {}

export interface ReferenceGetResponse {}

export interface ReferenceItem {
  id: string;
  title: string;
  content: string;
  type: string;
  metadata?: {
    [k: string]: unknown;
  } | null;
}

export interface ReferenceUpdateRequest {}

// Explicit re-export for build compatibility
export { ReferenceItem };
