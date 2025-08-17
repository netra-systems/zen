// Import canonical types from backend schema
import { ToolStatus, ToolInput, ToolResult } from './backend_schema_tools';

export interface ToolCompleted {
  tool_name: string;
  result: ToolResultData;
}

// Re-export for convenience
export { ToolStatus, ToolInput, ToolResult };

export interface ToolStarted {
  tool_name: string;
}

export interface ToolResultData {
  output?: string;
  data?: {
    [key: string]: unknown;
  };
  errors?: string[];
  warnings?: string[];
  metadata?: {
    [key: string]: unknown;
  };
}

export interface ToolPayload {
  type: string;
  data: {
    [key: string]: unknown;
  };
  timestamp?: number;
}
