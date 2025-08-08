import React, { useState } from 'react';
import { AgentUpdateMessage, ToolStatus } from '../types';

interface MessageProps {
    message: AgentUpdateMessage;
}

const Message: React.FC<MessageProps> = ({ message }) => {
    const { agent, messages, tools_status, todos } = message.data;
    const [isTodoOpen, setIsTodoOpen] = useState(false);

    return (
        <div className="bg-gray-800 p-4 rounded-lg mb-4">
            <div className="flex items-center mb-2">
                <div className="font-bold text-lg text-white">{agent}</div>
            </div>
            {tools_status && tools_status.length > 0 && (
                <div className="mb-2">
                    <div className="text-gray-400">Tools:</div>
                    <div className="flex flex-wrap">
                        {tools_status.map((tool, index) => (
                            <div key={index} className="bg-gray-700 rounded-full px-3 py-1 text-sm text-white mr-2 mb-2">
                                {tool.tool_name} - {tool.status}
                            </div>
                        ))}
                    </div>
                </div>
            )}
            <div>
                {messages.map((msg, index) => (
                    <div key={index} className="text-white">
                        {msg.content}
                    </div>
                ))}
            </div>
            {todos && todos.length > 0 && (
                <div>
                    <button onClick={() => setIsTodoOpen(!isTodoOpen)} className="text-blue-500">
                        {isTodoOpen ? 'Hide' : 'Show'} TODOs
                    </button>
                    {isTodoOpen && (
                        <div className="mt-2">
                            {todos.map((todo, index) => (
                                <div key={index} className="text-white">
                                    {todo.task}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default Message;
