import React from 'react';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { MessageFilter } from '@/app/hooks/useAgentStreaming';

interface MessageFilterProps {
    messageFilters: Set<MessageFilter>;
    setMessageFilters: React.Dispatch<React.SetStateAction<Set<MessageFilter>>>;
}

export function MessageFilterControl({ messageFilters, setMessageFilters }: MessageFilterProps) {
    const handleFilterChange = (filter: MessageFilter, checked: boolean) => {
        const newFilters = new Set(messageFilters);
        if (checked) {
            newFilters.add(filter);
        } else {
            newFilters.delete(filter);
        }
        setMessageFilters(newFilters);
    };

    return (
        <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
                <Switch
                    id="thinking-filter"
                    checked={messageFilters.has('thinking')}
                    onCheckedChange={(checked) => handleFilterChange('thinking', checked)}
                />
                <Label htmlFor="thinking-filter">Hide Thinking</Label>
            </div>
            <div className="flex items-center space-x-2">
                <Switch
                    id="event-filter"
                    checked={messageFilters.has('event')}
                    onCheckedChange={(checked) => handleFilterChange('event', checked)}
                />
                <Label htmlFor="event-filter">Hide Events</Label>
            </div>
        </div>
    );
}
