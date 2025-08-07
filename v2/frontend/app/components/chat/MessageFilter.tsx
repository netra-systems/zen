import React from 'react';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { MessageFilter } from '@/app/hooks/useAgentStreaming';

interface MessageFilterProps {
    messageFilters: Set<MessageFilter>;
    setMessageFilters: React.Dispatch<React.SetStateAction<Set<MessageFilter>>>;
    showThinking: boolean;
    setShowThinking: React.Dispatch<React.SetStateAction<boolean>>;
}

export function MessageFilterControl({ messageFilters, setMessageFilters, showThinking, setShowThinking }: MessageFilterControlProps) {
    const handleFilterChange = (filter: keyof MessageFilter, checked: boolean) => {
        const newFilters = { ...messageFilters };
        newFilters[filter] = checked;
        setMessageFilters(newFilters);
    };

    return (
        <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
                <Switch
                    id="thinking-filter"
                    checked={showThinking}
                    onCheckedChange={setShowThinking}
                />
                <Label htmlFor="thinking-filter">Show Thinking</Label>
            </div>
            <div className="flex items-center space-x-2">
                <Switch
                    id="event-filter"
                    checked={!messageFilters.event}
                    onCheckedChange={(checked) => handleFilterChange('event', !checked)}
                />
                <Label htmlFor="event-filter">Show Events</Label>
            </div>
        </div>
    );
}
