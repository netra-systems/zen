/* tslint:disable */
/* eslint-disable */
/**
 * Tool-related type definitions
 * Auto-generated from pydantic models - do not modify by hand
 */

export type ToolStatus = "success" | "error" | "partial_success" | "in_progress" | "complete";

export interface ToolCompleted {
  tool_name: string;
  result: unknown;
  run_id: string;
}

export interface ToolInput {
  tool_name: string;
  parameters: {
    [k: string]: unknown;
  };
}

export interface ToolInvocation {
  tool_name: string;
  parameters: {
    [k: string]: unknown;
  };
  run_id: string;
}

export interface ToolResult {
  tool_name: string;
  result: unknown;
  status: ToolStatus;
  error?: string | null;
  execution_time?: number | null;
  metadata?: {
    [k: string]: unknown;
  } | null;
}

export interface ToolStarted {
  tool_name: string;
  run_id: string;
}