// WebSocket error event handlers - Modular 25-line functions
// Handles error events and processing state management

import type { UnifiedWebSocketEvent } from '@/types/websocket-event-types';
import type { UnifiedChatState } from '@/types/store-types';
import type { ChatMessage } from '@/types/unified';
import { MessageFormatterService } from '@/services/messageFormatter';
import { generateUniqueId } from '../utils/unique-id-generator';

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
  const baseErrorMessage: ChatMessage = createErrorChatMessage(errorMessage);
  const enrichedErrorMessage = MessageFormatterService.enrich(baseErrorMessage);
  set({ isProcessing: false, messages: [...state.messages, enrichedErrorMessage] });
};

/**
 * Creates a chat message for error display
 */
const createErrorChatMessage = (errorMessage: string): ChatMessage => ({
  id: generateUniqueId('error'),
  role: 'system',
  content: errorMessage,
  timestamp: Date.now(),
  metadata: { messageType: 'error' }
});