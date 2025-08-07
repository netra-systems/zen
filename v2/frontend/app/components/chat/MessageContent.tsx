import React from 'react';
import Thinking from '@/components/Thinking';
import { Message, StateUpdateMessage, ToolEndMessage, MessageContentProps } from '@/app/types/index';
import JsonTreeView from './JsonTreeView';
// Replaced Heroicons with Lucid React for icons
import { AlertCircle, CheckCircle2, Cog, ListTodo } from 'lucide-react';

/**
 * A component responsible for rendering the specific content of a message
 * based on its type, now using Lucid for icons.
 */
export function MessageContent({ message }: MessageContentProps) {
    switch (message.type) {
        case 'user':
            return <p className="text-gray-800">{message.content}</p>;

        case 'text':
            return <p className="text-gray-800">{message.content}</p>;

        case 'thinking':
            return (
                <div className="flex items-center gap-2 text-gray-500">
                    <Thinking />
                    <p>{message.content || 'Thinking...'}</p>
                </div>
            );

        case 'error':
            return (
                <div className="flex items-center gap-2 text-red-600">
                    <AlertCircle className="h-5 w-5" />
                    <p>Error: {message.content}</p>
                </div>
            );
        
        case 'state_update':
            const stateMessage = message as StateUpdateMessage;
            return (
                <div className="p-4 my-2 border border-blue-200 bg-blue-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-3 text-blue-800">
                        <ListTodo className="h-5 w-5" />
                        <h3 className="font-semibold">Plan</h3>
                    </div>
                    <ul className="space-y-1">
                        {stateMessage.state.completed_steps.map((step, index) => (
                            <li key={`comp-${index}`} className="flex items-center gap-2 text-gray-500 line-through">
                                <CheckCircle2 className="h-5 w-5 text-green-500" />
                                {step}
                            </li>
                        ))}
                        {stateMessage.state.todo_list.map((step, index) => (
                            <li key={`todo-${index}`} className="flex items-center gap-2 text-gray-800">
                                <div className="h-5 w-5 flex items-center justify-center">
                                    <div className="h-2 w-2 border border-gray-400 rounded-full" />
                                </div>
                                {step}
                            </li>
                        ))}
                    </ul>
                </div>
            );

        case 'tool_start':
            return (
                <div className="p-4 my-2 border border-gray-200 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-2 text-gray-600">
                        <Cog className="h-5 w-5 animate-spin" />
                        <span className="font-semibold">{message.content}</span>
                    </div>
                    {message.toolInput && (
                        <div>
                           <h4 className="text-xs font-semibold text-gray-500 mb-1">INPUT</h4>
                           <JsonTreeView data={message.toolInput} />
                        </div>
                    )}
                </div>
            );

        case 'tool_end':
            const endMessage = message as ToolEndMessage;
            return (
                 <div className="p-4 my-2 border border-green-200 bg-green-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-3 text-green-800">
                        <CheckCircle2 className="h-5 w-5" />
                        <span className="font-semibold">{endMessage.tool} finished.</span>
                    </div>
                    {endMessage.toolInput && (
                        <div className="mb-3">
                           <h4 className="text-xs font-semibold text-gray-500 mb-1">INPUT</h4>
                           <JsonTreeView data={endMessage.toolInput} />
                        </div>
                    )}
                    {endMessage.tool_outputs?.map((output, index) => (
                         <div key={index}>
                           <h4 className="text-xs font-semibold text-gray-500 mb-1">OUTPUT</h4>
                           <JsonTreeView data={output.content} />
                        </div>
                    ))}
                </div>
            );

        default:
            return <pre className="text-xs text-gray-400">{JSON.stringify(message, null, 2)}</pre>;
    }
}