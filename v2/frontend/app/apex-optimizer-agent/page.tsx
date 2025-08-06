
import { useState, useEffect } from 'react';
import { startAgent, connectToWebSocket } from '../services/agentService';
import { AnalysisRequest } from '../types';


export default function ApexOptimizerAgentPage() {
    const [messages, setMessages] = useState<any[]>([]);
    const [input, setInput] = useState('');

    const handleSendMessage = async () => {
        const analysisRequest: AnalysisRequest = {
            user_request: input,
            user_id: 'user123',
            settings: {},
        };

        try {
            const result = await startAgent(analysisRequest, 'client123');
            const ws = connectToWebSocket(result.run_id, (message) => {
                setMessages((prevMessages) => [...prevMessages, message]);
            });

            // Clean up WebSocket connection when component unmounts
            return () => {
                ws.close();
            };
        } catch (error) {
            console.error(error);
        }
    };

    return (
        <div className="h-full flex flex-col">
            <div className="flex-grow p-4">
                {messages.map((message, index) => (
                    <div key={index}>{message.text}</div>
                ))}
            </div>
            <div className="p-4">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    className="w-full p-2 border rounded"
                />
                <button onClick={handleSendMessage} className="w-full p-2 mt-2 bg-blue-500 text-white rounded">
                    Send
                </button>
            </div>
        </div>
    );
}

