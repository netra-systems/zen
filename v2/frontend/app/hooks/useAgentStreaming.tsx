import { useState, useCallback } from 'react';
import { Message, Artifact } from '../types/chat';

export type MessageFilter = 'event';

function isJson(str: string) {
    try {
        JSON.parse(str);
    } catch {
        return false;
    }
    return true;
}

export function useAgentStreaming(initialMessages: Message[] = [], initialFilters: Set<MessageFilter> = new Set()) {
    const [messages, setMessages] = useState<Message[]>(initialMessages);
    const [messageFilters, setMessageFilters] = useState<Set<MessageFilter>>(initialFilters);
    const [showThinking, setShowThinking] = useState(false);

    const addMessage = useCallback((content: string, role: 'user' | 'agent' = 'user', event?: string, data?: any) => {
        const newMessage: Message = {
            id: `msg-${Date.now()}`,
            role,
            timestamp: new Date().toISOString(),
            type: event === 'on_chain_end' ? 'artifact' : 'text',
            content,
            artifact: event === 'on_chain_end' ? {
                type: 'analysis_result',
                content: content,
                data: data
            } : undefined
        };
        setMessages(prev => [...prev, newMessage]);
    }, []);

    const processStream = useCallback((chunk: string) => {
        if (isJson(chunk)) {
            const eventData = JSON.parse(chunk);
            const { event, data, run_id } = eventData;

            if (event === 'on_chat_model_stream') {
                setMessages(prev => {
                    const existingMessageIndex = prev.findIndex(m => m.id === run_id);
                    if (existingMessageIndex !== -1) {
                        const existingMessage = prev[existingMessageIndex];
                        if (existingMessage.type === 'thinking') {
                            const updatedMessage = {
                                ...existingMessage,
                                content: existingMessage.content + data.chunk.content,
                            };
                            const newMessages = [...prev];
                            newMessages[existingMessageIndex] = updatedMessage;
                            return newMessages;
                        }
                    } 
                    return [...prev, {
                        id: run_id,
                        role: 'agent',
                        timestamp: new Date().toISOString(),
                        type: 'thinking',
                        content: data.chunk.content,
                    }];
                });
            } else if (event === 'on_chain_end') {
                setMessages(prev => {
                    const existingMessageIndex = prev.findIndex(m => m.id === run_id);
                    if (existingMessageIndex !== -1) {
                        const newMessages = [...prev];
                        newMessages.splice(existingMessageIndex, 1);
                        return newMessages;
                    }
                    return prev;
                });
            } else {
                const newMessage: Message = {
                    id: run_id,
                    role: 'agent',
                    timestamp: new Date().toISOString(),
                    type: 'event',
                    name: event,
                    data: data,
                };
                setMessages(prev => [...prev, newMessage]);
            }
        } else {
            addMessage(chunk, 'agent');
        }
    }, [addMessage]);

    const filteredMessages = messages.filter(m => !messageFilters.has(m.type as MessageFilter));

    return {
        messages: filteredMessages,
        addMessage,
        messageFilters,
        setMessageFilters,
        showThinking,
        setShowThinking,
        processStream,
    };
}