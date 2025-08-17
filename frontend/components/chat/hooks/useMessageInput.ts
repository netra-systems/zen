import { useState, useRef, useEffect } from 'react';
import { MESSAGE_INPUT_CONSTANTS } from '../constants';
import { MessageInputState } from '../types';

const { MAX_ROWS, CHAR_LIMIT, LINE_HEIGHT } = MESSAGE_INPUT_CONSTANTS;

export const useMessageInput = () => {
  const [state, setState] = useState<MessageInputState>({
    message: '',
    rows: 1,
    isSending: false,
    messageHistory: [],
    historyIndex: -1
  });
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const updateMessage = (message: string) => {
    setState(prev => ({ ...prev, message }));
  };

  const updateRows = (rows: number) => {
    setState(prev => ({ ...prev, rows }));
  };

  const setIsSending = (isSending: boolean) => {
    setState(prev => ({ ...prev, isSending }));
  };

  const addToHistory = (message: string) => {
    setState(prev => ({
      ...prev,
      messageHistory: [...prev.messageHistory, message],
      historyIndex: -1
    }));
  };

  const setHistoryIndex = (index: number) => {
    setState(prev => ({ ...prev, historyIndex: index }));
  };

  const clearMessage = () => {
    setState(prev => ({
      ...prev,
      message: '',
      rows: 1
    }));
  };

  const navigateHistory = (direction: 'up' | 'down') => {
    const { messageHistory, historyIndex } = state;
    if (direction === 'up' && messageHistory.length > 0) {
      const newIndex = historyIndex === -1 
        ? messageHistory.length - 1 
        : Math.max(0, historyIndex - 1);
      setHistoryIndex(newIndex);
      updateMessage(messageHistory[newIndex]);
    } else if (direction === 'down' && historyIndex !== -1) {
      if (historyIndex < messageHistory.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        updateMessage(messageHistory[newIndex]);
      } else {
        setHistoryIndex(-1);
        updateMessage('');
      }
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      const newRows = Math.min(Math.ceil(scrollHeight / LINE_HEIGHT), MAX_ROWS);
      updateRows(newRows);
      textareaRef.current.style.height = `${scrollHeight}px`;
    }
  }, [state.message]);

  return {
    ...state,
    textareaRef,
    updateMessage,
    setIsSending,
    addToHistory,
    clearMessage,
    navigateHistory,
    isOverLimit: state.message.length > CHAR_LIMIT,
    isNearLimit: state.message.length > CHAR_LIMIT * 0.9
  };
};