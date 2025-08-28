import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
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

export const MessageInput: React.FC = () => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  const { activeThreadId, isProcessing } = useUnifiedChatStore();
  const { currentThreadId } = useThreadStore();
  const { isAuthenticated } = useAuthStore();
  
  const { messageHistory, addToHistory, navigateHistory } = useMessageHistory();
  const { rows } = useTextareaResize(textareaRef, message);
  const { isSending, handleSend } = useMessageSending();

  const focusTextarea = (): void => {
    if (textareaRef.current && isAuthenticated) {
      textareaRef.current.focus();
    }
  };

  useEffect(() => {
    focusTextarea();
  }, [isAuthenticated]);

  const resetMessageState = (): void => {
    setMessage('');
  };

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
              data-testid="char-count"
            >
              {message.length}/{CHAR_LIMIT}
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
};