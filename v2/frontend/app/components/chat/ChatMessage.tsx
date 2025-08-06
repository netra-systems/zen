import React from 'react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { Message } from '@/app/types/chat';
import { MessageContent } from './MessageContent';

export interface ChatMessageProps {
    message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
    const { role } = message;
    const isUser = role === 'user';

    return (
        <div className={cn('flex items-start gap-4', isUser ? 'justify-end' : '')}>
            {!isUser && (
                <Avatar className="h-8 w-8">
                    <AvatarFallback>AG</AvatarFallback>
                </Avatar>
            )}
            <Card className={cn(
                'max-w-[85%] transition-all duration-200 ease-in-out',
                isUser ? 'bg-primary text-primary-foreground' : 'bg-muted',
                { 'w-full max-w-4xl': message.type === 'artifact' || message.type === 'event' }
            )}>
                <CardContent className="p-3">
                    <MessageContent message={message} />
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