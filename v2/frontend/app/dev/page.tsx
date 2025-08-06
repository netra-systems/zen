
'use client';

import { useEffect, useState } from 'react';
import { connectToDevWebSocket } from '../services/devBypassService';

export default function DevPage() {
    const [messages, setMessages] = useState<string[]>([]);
    const [input, setInput] = useState('');
    const [ws, setWs] = useState<WebSocket | null>(null);

    useEffect(() => {
        const newWs = connectToDevWebSocket((message) => {
            setMessages((prev) => [...prev, message]);
        });
        setWs(newWs);

        return () => {
            newWs.close();
        };
    }, []);

    const sendMessage = () => {
        if (ws && input) {
            ws.send(input);
            setInput('');
        }
    };

    return (
        <div>
            <h1>Dev WebSocket Test</h1>
            <div>
                {messages.map((msg, i) => (
                    <div key={i}>{msg}</div>
                ))}
            </div>
            <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
            />
            <button onClick={sendMessage}>Send</button>
        </div>
    );
}
