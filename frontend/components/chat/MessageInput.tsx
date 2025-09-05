import React, { useState, useRef, useEffect, KeyboardEvent, forwardRef, useImperativeHandle } from 'react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { useMessageHistory } from './hooks/useMessageHistory';
import { useTextareaResize } from './hooks/useTextareaResize';
import { useMessageSending } from './hooks/useMessageSending';
import { MessageActionButtons } from './components/MessageActionButtons';
import { KeyboardShortcutsHint } from './components/KeyboardShortcutsHint';
import {
  getPlaceholder,
  getTextareaClassName,
  getCharCountClassName,
  shouldShowCharCount,
  isMessageDisabled,
  canSendMessage,
} from './utils/messageInputUtils';
import { MESSAGE_INPUT_CONSTANTS } from './types';

const { MAX_ROWS, CHAR_LIMIT, LINE_HEIGHT } = MESSAGE_INPUT_CONSTANTS;

export interface MessageInputRef {
  focus: () => void;
}

export interface MessageInputProps {
  onFirstInteraction?: () => void;
}

export const MessageInput = forwardRef<MessageInputRef, MessageInputProps>(({ onFirstInteraction }, ref) => {
  const [message, setMessage] = useState('');
  const [hasTriggeredFirstInteraction, setHasTriggeredFirstInteraction] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  const { activeThreadId, isProcessing } = useUnifiedChatStore();
  const { currentThreadId } = useThreadStore();
  const { isAuthenticated } = useAuthStore();
  
  const { messageHistory, addToHistory, navigateHistory } = useMessageHistory();
  const { rows } = useTextareaResize(textareaRef, message);
  const { 
    isSending, 
    error, 
    isTimeout, 
    retryCount, 
    isCircuitOpen, 
    handleSend, 
    retry,
    reset 
  } = useMessageSending();

  const focusTextarea = (): void => {
    if (textareaRef.current && isAuthenticated) {
      textareaRef.current.focus();
    }
  };

  // Expose focus method via ref
  useImperativeHandle(ref, () => ({
    focus: focusTextarea
  }), [isAuthenticated]);

  useEffect(() => {
    focusTextarea();
  }, [isAuthenticated]);

  const resetMessageState = (): void => {
    setMessage('');
  };

  // Reset first interaction state when starting new thread (message cleared externally)
  useEffect(() => {
    if (message === '' && hasTriggeredFirstInteraction) {
      // Only reset if this is likely a new thread (not just user clearing input)
      const timer = setTimeout(() => {
        if (message === '') {
          setHasTriggeredFirstInteraction(false);
        }
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [message, hasTriggeredFirstInteraction]);

  const onSend = async (): Promise<void> => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage) return;

    addToHistory(trimmedMessage);
    resetMessageState();
    
    await handleSend({
      message: trimmedMessage,
      activeThreadId,
      currentThreadId,
      isAuthenticated,
    });
  };

  const handleEnterKey = (e: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const handleHistoryNavigation = (
    e: KeyboardEvent<HTMLTextAreaElement>,
    direction: 'up' | 'down'
  ): void => {
    e.preventDefault();
    const historyMessage = navigateHistory(direction);
    setMessage(historyMessage);
  };

  const handleArrowKeys = (e: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (message !== '') return;
    
    if (e.key === 'ArrowUp' && messageHistory.length > 0) {
      handleHistoryNavigation(e, 'up');
    } else if (e.key === 'ArrowDown') {
      handleHistoryNavigation(e, 'down');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>): void => {
    handleEnterKey(e);
    handleArrowKeys(e);
    
    // Detect first real typing (not navigation keys)
    if (!hasTriggeredFirstInteraction && onFirstInteraction) {
      const isRealTyping = !['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Tab', 'Shift', 'Control', 'Alt', 'Meta', 'Escape', 'Enter'].includes(e.key);
      if (isRealTyping && e.key.length === 1) { // Single character keys only
        setHasTriggeredFirstInteraction(true);
        onFirstInteraction();
      }
    }
  };

  const placeholder = getPlaceholder(isAuthenticated, isProcessing, message.length);
  const textareaClassName = getTextareaClassName(message.length);
  const charCountClassName = getCharCountClassName(message.length);
  const isDisabled = isMessageDisabled(isProcessing, isAuthenticated, isSending);
  const canSend = canSendMessage(isDisabled, message, message.length);

  const textareaStyle = {
    minHeight: '48px',
    maxHeight: `${MAX_ROWS * LINE_HEIGHT + 24}px`,
    lineHeight: `${LINE_HEIGHT}px`
  };

  return (
    <div className="relative w-full" data-testid="message-input">
      <div className="flex items-end gap-2">
        <div className="flex-1 relative">
          <textarea
            id="message-input"
            name="message"
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={rows}
            disabled={isDisabled}
            className={textareaClassName}
            style={{...textareaStyle, height: `${rows * LINE_HEIGHT}px`}}
            aria-label="Message input"
            aria-describedby="char-count"
            data-testid="message-textarea"
          />
          
          {shouldShowCharCount(message.length) && (
            <div 
              id="char-count"
              className={charCountClassName}
              data-testid="character-count"
            >
              {message.length}/{CHAR_LIMIT}
            </div>
          )}
          
          {/* Error Messages and Recovery UI */}
          {error && (
            <div className="absolute top-full mt-2 left-0 right-0 bg-red-50 border border-red-200 rounded-md p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-red-600 text-sm">
                    {isTimeout ? 'Request timeout - ' : isCircuitOpen ? 'Service unavailable - ' : 'Error - '}
                    {error}
                  </span>
                  {retryCount > 0 && (
                    <span className="text-red-500 text-xs">
                      (Attempt {retryCount}/3)
                    </span>
                  )}
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => retry({ 
                      message, 
                      activeThreadId, 
                      currentThreadId, 
                      isAuthenticated 
                    })}
                    className="text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700"
                    disabled={isSending}
                  >
                    Try Again
                  </button>
                  <button
                    onClick={reset}
                    className="text-xs px-2 py-1 text-red-600 hover:text-red-800"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        <MessageActionButtons
          isDisabled={isDisabled}
          canSend={canSend}
          isSending={isSending}
          onSend={onSend}
        />
      </div>

      <KeyboardShortcutsHint 
        isAuthenticated={isAuthenticated}
        hasMessage={!!message}
      />
    </div>
  );
});

MessageInput.displayName = 'MessageInput';