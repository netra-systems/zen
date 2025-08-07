import React from 'react';
import Thinking from '@/components/Thinking';
import { Message } from '@/app/types/chat';
import JsonTreeView from './JsonTreeView';

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
                    <Thinking />
                    <p>{message.content || 'Thinking...'}</p>
                </div>
            );
        case 'error':
            return null;
        case 'tool_start':
            return (
                <div>
                    {message.toolInput && <JsonTreeView data={message.toolInput} />}
                </div>
            );
        case 'tool_end':
            return (
                <div>
                    {message.toolOutput && <JsonTreeView data={message.toolOutput} />}
                </div>
            );
        case 'state_update':
            return null;
        default:

            if (message.type == "user") {
                return (<div>
                    {message.content}
                </div> )
            }

            return <pre>{JSON.stringify(message, null, 2)}</pre>;
    }
}