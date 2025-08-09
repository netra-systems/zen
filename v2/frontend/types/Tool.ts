export type ToolStatus = "success" | "error" | "partial_success" | "in_progress" | "complete";

export interface ToolCompleted {
  tool_name: string;
  result: any;
}

export interface ToolInput {
  tool_name: string;
  args?: any[];
  kwargs?: {
    [k: string]: any;
  };
}

export interface ToolResult {
  tool_input: ToolInput;
  status?: ToolStatus;
  message?: string;
  payload?: any;
  start_time?: number;
  end_time?: number | null;
}

export interface ToolStarted {
  tool_name: string;
}
