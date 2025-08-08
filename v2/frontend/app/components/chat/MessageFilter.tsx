import React from 'react';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { MessageFilterControlProps, MessageFilter } from '@/app/types/index';

export function MessageFilterControl({ messageFilters, setMessageFilters, showThinking, setShowThinking }: MessageFilterControlProps) {
    const handleFilterChange = (filter: keyof MessageFilter, checked: boolean) => {
        const newFilters = { ...messageFilters, [filter]: checked };
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
                    checked={messageFilters.event}
                    onCheckedChange={(checked) => handleFilterChange('event', checked)}
                />
                <Label htmlFor="event-filter">Show Events</Label>
            </div>
            {/* Add more switches for other message types as needed */}
        </div>
    );
}