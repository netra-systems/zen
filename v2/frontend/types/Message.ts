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
