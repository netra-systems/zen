
import React from 'react';
import { Message } from '@/app/types/index';
import { AgentMessageCard } from './AgentMessageCard';
import { UserMessageCard } from './UserMessageCard';
import { Card, CardContent } from '@/components/ui/card';

interface ChatMessageProps {
    message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
    switch (message.type) {
        case 'agent':
            return <AgentMessageCard message={message} />;
        case 'user':
            return <UserMessageCard message={message} />;
        default:
            return (
                <Card className="w-full">
                    <CardContent>
                        <p>{message.content}</p>
                    </CardContent>
                </Card>
            );
    }
};
