import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { Message } from "@/types/index";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const truncatePrompt = (prompt: string, maxLength: number) => {
  const words = prompt.split(' ');
  if (words.length > maxLength) {
    return words.slice(0, maxLength).join(' ') + '...';
  }
  return prompt;
};

export const handleExampleClick = (query: string, setInput: (input: string) => void, onSendMessage: (message: string) => void) => {
    setInput(query);
    onSendMessage(query);
};

export const getTitle = (message: Message): string => {
    switch (message.type) {
        case 'tool_start':
        case 'tool_end':
            return message.tool || 'Tool';
        case 'state_update':
            return 'State Update';
        case 'tool_code':
            return 'Tool Code';
        case 'error':
            return 'Error';
        case 'user':
            return 'User';
        case 'assistant':
            return 'Assistant';
        default:
            return 'Message';
    }
};