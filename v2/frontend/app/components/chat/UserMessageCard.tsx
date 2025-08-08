
import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { UserMessage, Reference } from '@/app/types/index';

interface UserMessageCardProps {
    message: UserMessage;
}

const ReferenceDisplay: React.FC<{ reference: Reference }> = ({ reference }) => (
    <div className="reference-display mt-2">
        <p className="font-semibold">{reference.friendly_name}</p>
        <p className="text-sm text-muted-foreground">{reference.description}</p>
    </div>
);

export const UserMessageCard: React.FC<UserMessageCardProps> = ({ message }) => {
    return (
        <Card className="w-full bg-primary text-primary-foreground">
            <CardHeader>
                <CardTitle className="text-lg">You</CardTitle>
            </CardHeader>
            <CardContent>
                <p>{message.content}</p>
                {message.references && message.references.length > 0 && (
                    <div className="mt-4">
                        <h4 className="font-semibold">References:</h4>
                        {message.references.map((ref, index) => (
                            <ReferenceDisplay key={index} reference={ref} />
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
