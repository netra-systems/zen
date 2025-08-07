import React from 'react';
import { Message } from '@/app/types/chat';
import JsonTreeView from './JsonTreeView';

export interface MessageContentProps {
    message: Message;
}

export function MessageContent({ message }: MessageContentProps) {
    const renderContent = () => {
        if (typeof message.content === 'string') {
            try {
                const parsedContent = JSON.parse(message.content);
                return <JsonTreeView data={parsedContent} />;
            } catch (error) {
                // Not a JSON string, render as plain text
            }
        }
        return <p>{message.content}</p>;
    };

    switch (message.type) {
        case 'text':
            return renderContent();
        case 'thinking':
            return (
                <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900"></div>
                    <p>{message.content}</p>
                </div>
            );
        case 'event':
            return <JsonTreeView data={message} />;
        case 'artifact':
            return <p>{message.name}</p>;
        default:
            return null;
    }
}