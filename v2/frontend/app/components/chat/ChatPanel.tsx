import React, { useRef, useEffect } from 'react';
import { ChatMessage, ChatMessageProps } from './ChatMessage';

interface ChatPanelProps {
    messages: ChatMessageProps['message'][];
}

export function ChatPanel({ messages }: ChatPanelProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    return (
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message, index) => (
                <ChatMessage key={index} message={message} />
            ))}
        </div>
    );
}