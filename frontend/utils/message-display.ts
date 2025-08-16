/**
 * Message Display Utilities
 * 
 * Utilities for handling message display logic, particularly for agent name display.
 * This module follows the 8-line function limit and provides clean, type-safe utilities.
 */

import { MessageType } from '@/types/backend_schema_base';

/**
 * Determines if a sub-agent name is valid for display
 */
export function isValidSubAgentName(subAgentName: string | null | undefined): boolean {
  if (!subAgentName) return false;
  if (subAgentName === 'undefined') return false;
  if (subAgentName.trim() === '') return false;
  return true;
}

/**
 * Gets the display name for a message based on type and sub-agent name
 */
export function getMessageDisplayName(
  messageType: MessageType,
  subAgentName?: string | null
): string {
  if (messageType === 'user') return 'You';
  if (isValidSubAgentName(subAgentName)) return subAgentName!;
  return 'Netra Agent';
}

/**
 * Gets the display subtitle for non-user messages with valid sub-agent names
 */
export function getMessageSubtitle(
  messageType: MessageType,
  subAgentName?: string | null
): string | null {
  if (messageType === 'user') return null;
  if (!isValidSubAgentName(subAgentName)) return null;
  if (messageType === 'tool') return 'Tool Execution';
  return 'Agent Response';
}

/**
 * Determines if a message should show a subtitle
 */
export function shouldShowSubtitle(
  messageType: MessageType,
  subAgentName?: string | null
): boolean {
  return getMessageSubtitle(messageType, subAgentName) !== null;
}