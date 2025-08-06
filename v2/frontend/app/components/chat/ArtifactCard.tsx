import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { JsonTreeView } from './JsonTreeView';
import { Message } from '@/app/types/chat';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';

export interface ArtifactCardProps {
    message: Message;
}

function renderFriendlyArtifactData(data: any) {
    if (!data) return <p>No data available</p>;

    const renderValue = (value: any) => {
        if (typeof value === 'object' && value !== null) {
            return <JsonTreeView data={value} />;
        }
        return String(value);
    }

    // Example of rendering specific data points in a user-friendly way
    return (
        <div className="space-y-2">
            {Object.entries(data).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                    <span className="font-semibold">{key}:</span>
                    <span>{renderValue(value)}</span>
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
                    <Accordion type="single" collapsible className="w-full">
                        <AccordionItem value="item-1">
                            <AccordionTrigger>View Details</AccordionTrigger>
                            <AccordionContent>
                                {renderFriendlyArtifactData(data)}
                            </AccordionContent>
                        </AccordionItem>
                    </Accordion>
                )}
            </CardContent>
        </Card>
    );
}
