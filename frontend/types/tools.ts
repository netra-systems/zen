/* tslint:disable */
/* eslint-disable */
/**
 * Tool-related type definitions
 * Auto-generated from pydantic models - do not modify by hand
 */

import { ToolStatus, ToolInput, ToolResult } from './backend_schema_tools';

// Re-export canonical types
export { ToolStatus, ToolInput, ToolResult };

export interface ToolCompleted {
  tool_name: string;
  result: unknown;
  run_id: string;
}

export interface ToolInvocation {
  tool_name: string;
  parameters: {
    [k: string]: unknown;
  };
  run_id: string;
}

export interface ToolStarted {
  tool_name: string;
  run_id: string;
}