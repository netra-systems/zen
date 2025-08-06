import React from 'react';
import { Message } from '@/app/types/chat';

export interface MessageContentProps {
    message: Message;
}

export function MessageContent({ message }: MessageContentProps) {
    switch (message.type) {
        case 'text':
            return <p>{message.content}</p>;
        case 'thinking':
            return (
                <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900"></div>
                    <p>{message.content}</p>
                </div>
            );
        case 'event':
        case 'artifact':
            return <p>{message.name}</p>;
        default:
            const exhaustiveCheck: never = message;
            return null;
    }
}
