
import React, { useState } from 'react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { MessageArtifact } from './MessageArtifact';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface Message {
    role: 'user' | 'agent';
    content: React.ReactNode;
    isThinking?: boolean;
    artifacts?: any[];
}

export interface ChatMessageProps {
    message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
    const { role, content, isThinking, artifacts } = message;
    const isUser = role === 'user';
    const [showThinking, setShowThinking] = useState(false);

    const renderContent = () => {
        if (isThinking && typeof content === 'object' && content !== null) {
            return <MessageArtifact data={content} />;
        }
        if (typeof content === 'string') {
            return <p className="text-sm" style={{ whiteSpace: 'pre-wrap' }}>{content}</p>;
        }
        return content;
    };

    const hasArtifacts = artifacts && artifacts.length > 0;

    return (
        <div className={cn('flex items-start gap-4 group', isUser ? 'justify-end' : 'flex-col items-start')}>
            <div className={cn('flex items-start gap-4 w-full', isUser ? 'justify-end' : 'justify-start')}>
                {!isUser && (
                    <Avatar className="h-8 w-8">
                        <AvatarFallback>AG</AvatarFallback>
                    </Avatar>
                )}
                <Card className={cn(
                    'max-w-[85%] transition-all duration-200 ease-in-out',
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
            
            {hasArtifacts && !isUser && (
                <div className="w-full flex justify-start pl-12">
                    <Button variant="outline" size="sm" onClick={() => setShowThinking(!showThinking)} className="mt-2">
                        {showThinking ? <ChevronUp className="h-4 w-4 mr-2" /> : <ChevronDown className="h-4 w-4 mr-2" />}
                        {showThinking ? 'Hide Thinking' : 'Show Thinking'}
                    </Button>
                </div>
            )}

            {showThinking && hasArtifacts && (
                <div className="w-full pl-12 mt-2 space-y-2">
                    {artifacts.map((artifact, index) => (
                        <MessageArtifact key={index} data={artifact} />
                    ))}
                </div>
            )}
        </div>
    );
}