
import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { UserMessage, Reference } from '@/app/types/index';

interface UserMessageCardProps {
    message: UserMessage;
}

const ReferenceDisplay: React.FC<{ reference: Reference }> = ({ reference }) => (
    <div className="reference-display mt-2 border p-4 rounded-lg bg-blue-50 dark:bg-blue-900">
        <p className="font-semibold text-md text-blue-800 dark:text-blue-200">{reference.friendly_name}</p>
        <p className="text-sm text-blue-600 dark:text-blue-400">{reference.description}</p>
    </div>
);

export const UserMessageCard: React.FC<UserMessageCardProps> = ({ message }) => {
    return (
        <Card className="w-full bg-blue-600 text-white rounded-xl shadow-lg">
            <CardHeader className="p-6">
                <CardTitle className="text-2xl font-bold">You</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
                <p className="text-lg">{message.content}</p>
                {message.references && message.references.length > 0 && (
                    <div className="mt-6">
                        <h4 className="font-semibold text-xl mb-4">References:</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {message.references.map((ref, index) => (
                                <ReferenceDisplay key={index} reference={ref} />
                            ))}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
