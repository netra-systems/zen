
import React from 'react';
import { Message } from '@/app/types/chat';
import { ChatMessage } from './ChatMessage';
import { ArtifactCard } from './ArtifactCard';

export interface MessageOrchestratorProps {
    message: Message;
    showThinking: boolean;
}

export function MessageOrchestrator({ message, showThinking }: MessageOrchestratorProps) {
    if (message.type === 'thinking' && !showThinking) {
        return null;
    }

    if (message.type === 'artifact' || message.type === 'event') {
        return <ArtifactCard message={message} />;
    }

    return <ChatMessage message={message} />;
}
