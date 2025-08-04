
import React from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface Message {
    role: 'user' | 'agent';
    content: React.ReactNode;
}

export interface ChatMessageProps {
    message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
    const { role, content } = message;
    const isUser = role === 'user';

    return (
        <div className={cn('flex items-start gap-4', isUser ? 'justify-end' : '')}>
            {!isUser && (
                <Avatar className="h-8 w-8">
                    <AvatarFallback>AG</AvatarFallback>
                </Avatar>
            )}
            <Card className={cn('max-w-[75%]', isUser ? 'bg-primary text-primary-foreground' : 'bg-muted')}>
                <CardContent className="p-3">
                    {typeof content === 'string' ? (
                        <p className="text-sm">{content}</p>
                    ) : (
                        content
                    )}
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
