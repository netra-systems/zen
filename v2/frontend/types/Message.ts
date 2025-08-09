export interface Message {
  id: string;
  created_at: string;
  content: string;
  type: "user" | "agent" | "system" | "error" | "tool";
  sub_agent_name?: string | null;
  tool_info?: { [k: string]: any } | null;
  raw_data?: { [k: string]: any } | null;
  displayed_to_user?: boolean;
}

export interface UserMessage {
  text: string;
  references?: string[];
}

export interface AgentMessage {
  text: string;
}

export interface MessageToUser {
  sender: string;
  content: string;
  references?: string[] | null;
  raw_json?: { [k: string]: any } | null;
  error?: string | null;
}