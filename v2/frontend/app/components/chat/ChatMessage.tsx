import React from 'react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { MessageArtifact } from './MessageArtifact';

interface Message {
    role: 'user' | 'agent';
    content: React.ReactNode;
    isThinking?: boolean;
}

export interface ChatMessageProps {
    message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
    const { role, content, isThinking } = message;
    const isUser = role === 'user';

    const renderContent = () => {
        if (isThinking && typeof content === 'object' && content !== null) {
            return <MessageArtifact data={content} />;
        }
        if (typeof content === 'string') {
            return <p className="text-sm">{content}</p>;
        }
        return content;
    };

    return (
        <div className={cn('flex items-start gap-4 group', isUser ? 'justify-end' : '')}>
            {!isUser && (
                <Avatar className="h-8 w-8">
                    <AvatarFallback>AG</AvatarFallback>
                </Avatar>
            )}
            <Card className={cn(
                'max-w-[75%] transition-all duration-200 ease-in-out',
                isUser ? 'bg-primary text-primary-foreground' : 'bg-muted',
                { 'w-full max-w-4xl': isThinking }
            )}>
                <CardContent className="p-3">
                    {renderContent()}
                </CardContent>
            </Card>
            {isUser && (
                <Avatar className="h-8 w-8">
                    <AvatarFallback>YOU</AvatarFallback>
                </Avatar>
            )}
        </div>
    );
}