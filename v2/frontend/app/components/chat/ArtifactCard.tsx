import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { JsonTreeView } from './JsonTreeView';
import { Message } from '@/app/types/chat';

export interface ArtifactCardProps {
    message: Message;
}

function renderFriendlyArtifactData(data: any) {
    if (!data) return <p>No data available</p>;

    // Example of rendering specific data points in a user-friendly way
    return (
        <div className="space-y-2">
            {Object.entries(data).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                    <span className="font-semibold">{key}:</span>
                    <span>{String(value)}</span>
                </div>
            ))}
        </div>
    );
}

export function ArtifactCard({ message }: ArtifactCardProps) {
    const [showJson, setShowJson] = useState(false);

    if (message.type !== 'artifact' && message.type !== 'event') {
        return null;
    }

    const { name, data } = message;

    return (
        <Card className="w-full">
            <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>{name}</CardTitle>
                <Button variant="outline" size="sm" onClick={() => setShowJson(!showJson)}>
                    {showJson ? 'Hide JSON' : 'Show JSON'}
                </Button>
            </CardHeader>
            <CardContent>
                {showJson ? (
                    <JsonTreeView data={data} />
                ) : (
                    renderFriendlyArtifactData(data)
                )}
            </CardContent>
        </Card>
    );
}
