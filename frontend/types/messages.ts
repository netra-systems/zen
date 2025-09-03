/* tslint:disable */
/* eslint-disable */
/**
 * Message-related type definitions
 * Auto-generated from pydantic models - do not modify by hand
 */

// Import consolidated types from backend schema
import type {
  BaseMessage,
  Message,
  MessageType,
  StreamEvent
} from './backend_schema_base';
import type { ReferenceItem } from './backend_schema_tools';

// Re-export for backward compatibility
export type {
  BaseMessage,
  Message,
  MessageType,
  ReferenceItem,
  StreamEvent
};

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

export interface RunComplete {
  run_id: string;
  final_output: string;
}

