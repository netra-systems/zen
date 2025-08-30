import { cn } from '@/lib/utils';
import { MESSAGE_INPUT_CONSTANTS } from '../types';

const { CHAR_LIMIT } = MESSAGE_INPUT_CONSTANTS;

export const getPlaceholder = (
  isAuthenticated: boolean,
  isProcessing: boolean,
  messageLength: number
): string => {
  if (!isAuthenticated) return 'Please sign in to send messages';
  if (isProcessing) return 'Agent is thinking...';
  if (messageLength > CHAR_LIMIT * 0.9) {
    return `${CHAR_LIMIT - messageLength} characters remaining`;
  }
  return 'Start typing your AI optimization request... (Shift+Enter for new line)';
};

export const getTextareaClassName = (messageLength: number): string => {
  return cn(
    "w-full resize-none rounded-2xl px-4 py-3 pr-12",
    "bg-gray-50 border border-gray-200",
    "focus:bg-white focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100",
    "transition-all duration-200 ease-in-out",
    "placeholder:text-gray-400 text-gray-900",
    "disabled:opacity-50 disabled:cursor-not-allowed",
    messageLength > CHAR_LIMIT * 0.9 && "border-orange-400 focus:ring-orange-100",
    messageLength > CHAR_LIMIT && "border-red-400 focus:ring-red-100"
  );
};

export const getCharCountClassName = (messageLength: number): string => {
  return cn(
    "absolute bottom-2 right-2 text-xs font-medium",
    messageLength > CHAR_LIMIT ? "text-red-500" : 
    messageLength > CHAR_LIMIT * 0.9 ? "text-orange-500" : "text-gray-400"
  );
};

export const shouldShowCharCount = (messageLength: number): boolean => {
  return messageLength > CHAR_LIMIT * 0.8;
};

export const isMessageDisabled = (
  isProcessing: boolean,
  isAuthenticated: boolean,
  isSending: boolean
): boolean => {
  return isProcessing || !isAuthenticated || isSending;
};

export const canSendMessage = (
  isDisabled: boolean,
  message: string,
  messageLength: number
): boolean => {
  return !isDisabled && !!message.trim() && messageLength <= CHAR_LIMIT;
};