export type ToolStatus = "success" | "error" | "partial_success" | "in_progress" | "complete";

export interface ToolCompleted {
  tool_name: string;
  result: ToolResultData;
}

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
  payload?: ToolPayload;
  start_time?: number;
  end_time?: number | null;
}

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
