import React from 'react';
import { Message } from '@/types/index';
import { AgentMessageCard } from './AgentMessageCard';
import { UserMessageCard } from './UserMessageCard';
import { ThinkingMessage, ErrorMessage, EventMessage, TextMessage } from '@/types/index';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ChatMessageProps {
    message: Message;
}

const ThinkingCard: React.FC<{ message: ThinkingMessage }> = ({ message }) => (
    <Card className="w-full animate-pulse">
        <CardHeader>
            <CardTitle className="text-lg">Thinking...</CardTitle>
        </CardHeader>
        <CardContent>
            <p>{message.content}</p>
        </CardContent>
    </Card>
);

const ErrorCard: React.FC<{ message: ErrorMessage }> = ({ message }) => (
    <Card className="w-full bg-destructive text-destructive-foreground">
        <CardHeader>
            <CardTitle className="text-lg">Error</CardTitle>
        </CardHeader>
        <CardContent>
            <p>{message.content}</p>
        </CardContent>
    </Card>
);

const EventCard: React.FC<{ message: EventMessage }> = ({ message }) => (
    <Card className="w-full bg-muted text-muted-foreground">
        <CardHeader>
            <CardTitle className="text-lg">{message.eventName}</CardTitle>
        </CardHeader>
        <CardContent>
            <p>{message.content}</p>
        </CardContent>
    </Card>
);

const TextCard: React.FC<{ message: TextMessage }> = ({ message }) => (
    <Card className="w-full">
        <CardContent>
            <p>{message.content}</p>
        </CardContent>
    </Card>
);

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
    switch (message.type) {
        case 'agent':
            return <AgentMessageCard message={message} />;
        case 'user':
            return <UserMessageCard message={message} />;
        case 'thinking':
            return <ThinkingCard message={message} />;
        case 'error':
            return <ErrorCard message={message} />;
        case 'event':
            return <EventCard message={message} />;
        case 'text':
            return <TextCard message={message} />;
        default:
            return null; // Or a default card for unhandled message types
    }
};