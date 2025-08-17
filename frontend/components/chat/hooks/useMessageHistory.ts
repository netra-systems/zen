import { useState } from 'react';
import { MessageHistoryActions } from '../types';

export const useMessageHistory = (): MessageHistoryActions & {
  messageHistory: string[];
  historyIndex: number;
} => {
  const [messageHistory, setMessageHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const addToHistory = (message: string): void => {
    setMessageHistory(prev => [...prev, message]);
    setHistoryIndex(-1);
  };

  const getUpDirection = (): number => {
    return historyIndex === -1 
      ? messageHistory.length - 1 
      : Math.max(0, historyIndex - 1);
  };

  const getDownDirection = (): number => {
    return Math.min(messageHistory.length - 1, historyIndex + 1);
  };

  const handleUpNavigation = (): string => {
    const newIndex = getUpDirection();
    setHistoryIndex(newIndex);
    return messageHistory[newIndex];
  };

  const handleDownNavigation = (): string => {
    const newIndex = getDownDirection();
    if (newIndex === messageHistory.length - 1) {
      setHistoryIndex(-1);
      return '';
    }
    setHistoryIndex(newIndex);
    return messageHistory[newIndex];
  };

  const navigateHistory = (direction: 'up' | 'down'): string => {
    if (direction === 'up' && messageHistory.length > 0) {
      return handleUpNavigation();
    }
    if (direction === 'down' && historyIndex !== -1) {
      return handleDownNavigation();
    }
    return '';
  };

  const resetHistory = (): void => {
    setHistoryIndex(-1);
  };

  return {
    messageHistory,
    historyIndex,
    addToHistory,
    navigateHistory,
    resetHistory,
  };
};