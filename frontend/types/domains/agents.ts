/**
 * Agent Domain Types - Consolidated Agent Type Definitions
 * 
 * This module contains all agent-related type definitions and serves as the single source
 * of truth for agent state, metadata, and lifecycle management in the Netra frontend.
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - Maximum file size: 300 lines
 * - All functions: ≤8 lines
 * - Single source of truth for agent types
 * 
 * BVJ: Consolidated agent types = fewer bugs = smoother agent operations = better customer retention
 */

import { AgentStatus } from '../shared/enums';

// ============================================================================
// TOOL AND EXECUTION TYPES
// ============================================================================

/**
 * Data structure for tool execution results within agent workflows.
 * Provides standardized tracking of tool performance and outcomes.
 */
export interface ToolResultData {
  tool_name: string;
  status: string;
  output?: string | Record<string, unknown> | Array<unknown> | null;
  error?: string | null;
  execution_time_ms?: number | null;
  metadata?: Record<string, string | number | boolean>;
}

/**
 * Metadata container for agent lifecycle tracking and debugging.
 * Essential for performance monitoring and agent optimization.
 */
export interface AgentMetadata {
  created_at?: string; // ISO datetime string
  last_updated?: string; // ISO datetime string  
  execution_context?: Record<string, string>;
  custom_fields?: Record<string, string>;
  priority?: number | null; // 0-10
  retry_count?: number;
  parent_agent_id?: string | null;
  tags?: string[];
}

/**
 * Standardized result structure for all agent operations.
 * Supports both new format and legacy backend compatibility.
 */
export interface AgentResult {
  success: boolean;
  output?: string | Record<string, unknown> | Array<unknown> | null;
  error?: string | null;
  metrics?: Record<string, number>;
  artifacts?: string[];
  execution_time_ms?: number | null;
  // Backend compatibility
  message?: string;
  data?: string | Record<string, unknown> | unknown[];
}

// ============================================================================
// MESSAGE AND COMMUNICATION TYPES
// ============================================================================

/**
 * Message data structure for agent communication and thread management.
 * Standardized across all communication channels.
 */
export interface MessageData {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  timestamp: string; // ISO datetime string
  metadata?: Record<string, string | number | boolean>;
}

/**
 * Response structure for thread history retrieval operations.
 * Used in agent conversation context management.
 */
export interface ThreadHistoryResponse {
  thread_id: string;
  messages: MessageData[];
}

// ============================================================================
// AGENT STATE MANAGEMENT
// ============================================================================

/**
 * Core agent state interface for comprehensive agent lifecycle management.
 * Consolidates all agent execution data and status tracking.
 */
export interface AgentState {
  user_request: string;
  chat_thread_id?: string | null;
  user_id?: string | null;
  
  // Status and lifecycle
  status?: AgentStatus;
  start_time?: string | null; // ISO datetime string
  end_time?: string | null; // ISO datetime string
  
  // Results from different agent types  
  triage_result?: unknown | null;
  data_result?: unknown | null;
  optimizations_result?: unknown | null;
  action_plan_result?: unknown | null;
  report_result?: unknown | null;
  synthetic_data_result?: unknown | null;
  supply_research_result?: unknown | null;
  
  // Execution tracking
  final_report?: string | null;
  step_count?: number;
  tool_results?: ToolResultData[] | null;
  error_message?: string | null;
  error_details?: Record<string, string | number | Record<string, unknown>> | null;
  performance_metrics?: Record<string, number>;
  
  // Metadata
  metadata?: AgentMetadata;
}

// ============================================================================
// SUB-AGENT TYPES (Consolidated from backend_schema_base.ts)
// ============================================================================

/**
 * Sub-agent lifecycle states for tracking nested agent operations.
 */
export type SubAgentLifecycle = "pending" | "running" | "completed" | "failed" | "shutdown";

/**
 * Base message structure for agent communication.
 */
export interface BaseMessage {
  role: "user" | "agent" | "system" | "error" | "tool";
  content: string;
  timestamp?: string;
}

/**
 * Sub-agent state for nested agent workflow management.
 * Tracks individual sub-agent execution within larger workflows.
 */
export interface SubAgentState {
  messages: BaseMessage[];
  next_node: string;
  tool_results?: { [k: string]: unknown; }[] | null;
  lifecycle?: SubAgentLifecycle;
  start_time?: string | null;
  end_time?: string | null;
  error_message?: string | null;
  agent_id?: string;
  status?: SubAgentLifecycle;
  result?: unknown | null;
  error?: string | null;
}

/**
 * Status tracking for sub-agent collections and hierarchies.
 */
export interface SubAgentStatus {
  agent_name: string;
  tools: string[];
  status: string;
  agents?: SubAgentState[];
}

// ============================================================================
// VALIDATION HELPERS - All functions ≤8 lines
// ============================================================================

/**
 * Validates if an agent state has all required fields.
 * @param state - The agent state to validate
 * @returns True if valid, false otherwise
 */
export function isValidAgentState(state: Partial<AgentState>): state is AgentState {
  return !!(state.user_request && typeof state.user_request === 'string');
}

/**
 * Checks if agent is in an active execution state.
 * @param status - The agent status to check
 * @returns True if agent is actively running
 */
export function isAgentActive(status?: AgentStatus): boolean {
  const activeStates = [AgentStatus.ACTIVE, AgentStatus.EXECUTING, AgentStatus.RUNNING];
  return status ? activeStates.includes(status) : false;
}

/**
 * Checks if agent has completed successfully.
 * @param state - The agent state to check
 * @returns True if agent completed successfully
 */
export function isAgentCompleted(state: AgentState): boolean {
  return state.status === AgentStatus.COMPLETED && !state.error_message;
}

/**
 * Checks if agent is in error state.
 * @param state - The agent state to check
 * @returns True if agent has errors
 */
export function hasAgentError(state: AgentState): boolean {
  const errorStates = [AgentStatus.ERROR, AgentStatus.FAILED];
  return errorStates.includes(state.status!) || !!state.error_message;
}

/**
 * Extracts agent execution duration in milliseconds.
 * @param state - The agent state
 * @returns Duration in ms or null if incomplete
 */
export function getAgentDuration(state: AgentState): number | null {
  if (!state.start_time || !state.end_time) return null;
  const start = new Date(state.start_time).getTime();
  const end = new Date(state.end_time).getTime();
  return end - start;
}

/**
 * Validates sub-agent lifecycle state.
 * @param lifecycle - The lifecycle state to validate
 * @returns True if valid lifecycle state
 */
export function isValidSubAgentLifecycle(lifecycle: string): lifecycle is SubAgentLifecycle {
  const validStates: SubAgentLifecycle[] = ["pending", "running", "completed", "failed", "shutdown"];
  return validStates.includes(lifecycle as SubAgentLifecycle);
}

/**
 * Creates a default agent metadata object with current timestamp.
 * @param customFields - Optional custom fields to include
 * @returns New AgentMetadata instance
 */
export function createAgentMetadata(customFields?: Record<string, string>): AgentMetadata {
  const now = new Date().toISOString();
  return {
    created_at: now,
    last_updated: now,
    custom_fields: customFields,
    retry_count: 0,
    tags: []
  };
}

/**
 * Updates agent metadata with new timestamp and optional fields.
 * @param metadata - Existing metadata to update
 * @param updates - Partial updates to apply
 * @returns Updated metadata object
 */
export function updateAgentMetadata(
  metadata: AgentMetadata, 
  updates: Partial<AgentMetadata>
): AgentMetadata {
  return {
    ...metadata,
    ...updates,
    last_updated: new Date().toISOString()
  };
}