import { useState, useEffect, useCallback } from 'react';
import { Message } from './types/chat';

export type MessageFilter = 'thinking' | 'event';

export function useAgentStreaming(initialMessages: Message[] = [], initialFilters: Set<MessageFilter> = new Set(['thinking'])) {
    const [messages, setMessages] = useState<Message[]>(initialMessages);
    const [messageFilters, setMessageFilters] = useState<Set<MessageFilter>>(initialFilters);

    const processStream = useCallback((chunk: string) => {
        // This is a placeholder for the actual stream processing logic.
        // In a real implementation, this would parse the incoming chunk
        // and update the messages state accordingly.
        const newMessage: Message = {
            id: `msg-${Date.now()}`,
            role: 'agent',
            timestamp: new Date().toISOString(),
            type: 'text',
            content: chunk,
        };
        setMessages(prev => [...prev, newMessage]);
    }, []);

    const filteredMessages = messages.filter(m => !messageFilters.has(m.type as MessageFilter));

    return {
        messages: filteredMessages,
        addMessage: (content: string, role: 'user' | 'agent' = 'user') => {
            const newMessage: Message = {
                id: `msg-${Date.now()}`,
                role,
                timestamp: new Date().toISOString(),
                type: 'text',
                content,
            };
            setMessages(prev => [...prev, newMessage]);
        },
        messageFilters,
        setMessageFilters,
        processStream,
    };
}
