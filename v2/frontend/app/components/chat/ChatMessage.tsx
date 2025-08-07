import React from 'react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { Message } from '@/app/types/chat';
import { MessageCard } from '../MessageCard';
import { useUser } from '@/lib/user';

export interface ChatMessageProps {
    message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
    const { user } = useUser();
    const { role } = message;
    const isUser = role === 'user';

    return (
        <div className={cn('flex items-start gap-4', isUser ? 'justify-end' : '')}> 
            <MessageCard message={message} user={{ name: user?.full_name || 'Unknown', picture: user?.picture }} />
        </div>
    );
}