'use client';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { ChatMessage } from '@/types';

export function MessageCard({ message, user }: { message: ChatMessage, user: any }) {
    const { data } = message;

    return (
        <Card className="flex items-start gap-4 p-4">
            <Avatar>
                <AvatarImage src={data.sub_agent_name ? "/agent-avatar.png" : user?.picture} />
                <AvatarFallback>{data.sub_agent_name ? 'A' : user?.name?.charAt(0).toUpperCase()}</AvatarFallback>
            </Avatar>
            <div className="rounded-lg p-3 max-w-[75%] bg-muted">
                <div className="flex flex-col">
                    {data.sub_agent_name && (
                        <CardHeader>
                            <CardTitle>{data.sub_agent_name}</CardTitle>
                        </CardHeader>
                    )}
                    <CardContent>
                        {data.tools_used && (
                            <div className="text-xs text-gray-500">
                                Tools: {data.tools_used.join(', ')}
                            </div>
                        )}
                        {data.ai_message && <p>{data.ai_message}</p>}
                        {data.user_message && <p>{data.user_message}</p>}
                        {data.tool_todo_list && (
                            <Accordion type="single" collapsible className="w-full mt-2">
                                <AccordionItem value="item-1">
                                    <AccordionTrigger className="text-xs text-gray-500">TODO List</AccordionTrigger>
                                    <AccordionContent>
                                        <ul>
                                            {data.tool_todo_list.map((todo: any, index: number) => (
                                                <li key={index}>{todo.task}</li>
                                            ))}
                                        </ul>
                                    </AccordionContent>
                                </AccordionItem>
                            </Accordion>
                        )}
                        {data.tool_errors && (
                            <div className="mt-2 text-red-500">
                                {data.tool_errors.map((error, index) => (
                                    <p key={index}>Error in {error.tool_name}: {error.error_message}</p>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </div>
            </div>
        </Card>
    );
}