// WebSocket error event handlers - Modular 8-line functions
// Handles error events and processing state management

import type { UnifiedWebSocketEvent } from '@/types/websocket-event-types';
import type { UnifiedChatState } from '@/types/store-types';
import type { ChatMessage } from '@/types/chat';

/**
 * Handles error events - sets processing to false and adds error message
 */
export const handleError = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState
): void => {
  const errorMessage = (event.payload as any).error_message || 'An error occurred';
  const errorChatMessage: ChatMessage = createErrorChatMessage(errorMessage);
  set({ isProcessing: false, messages: [...state.messages, errorChatMessage] });
};

/**
 * Creates a chat message for error display
 */
const createErrorChatMessage = (errorMessage: string): ChatMessage => ({
  id: `error-${Date.now()}`,
  role: 'system',
  content: errorMessage,
  timestamp: Date.now(),
  metadata: { messageType: 'error' }
});