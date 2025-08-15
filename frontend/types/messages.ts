/* tslint:disable */
/* eslint-disable */
/**
 * Message-related type definitions
 * Auto-generated from pydantic models - do not modify by hand
 */

export type MessageType = "user" | "agent" | "system" | "error" | "tool";

export interface BaseMessage {
  content:
    | string
    | (
        | string
        | {
            [k: string]: unknown;
          }
      )[];
  additional_kwargs?: {
    [k: string]: unknown;
  } | null;
  response_metadata?: {
    [k: string]: unknown;
  } | null;
  type: string;
  name?: string | null;
  id?: string | null;
}

export interface Message {
  id: string;
  thread_id?: string | null;
  content: string;
  role: MessageType;
  created_at?: string | null;
  updated_at?: string | null;
  references?: ReferenceItem[] | null;
  metadata?: {
    [k: string]: unknown;
  } | null;
}

export interface MessageToUser {
  content: string;
  type: string;
  id?: string | null;
}

export interface UserMessage {
  text: string;
  thread_id?: string | null;
  references?: ReferenceItem[] | null;
}

export interface StreamEvent {
  event: string;
  data: unknown;
  id?: string | null;
  retry?: number | null;
}

export interface RunComplete {
  run_id: string;
  final_output: string;
}

// Re-export types needed by messages
export interface ReferenceItem {
  id: string;
  title: string;
  content: string;
  type: string;
  metadata?: {
    [k: string]: unknown;
  } | null;
}