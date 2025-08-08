import React, { useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

interface ChatProps {
    runId: string;
}

const Chat: React.FC<ChatProps> = ({ runId }) => {
    const { messages, sendMessage, isConnected } = useWebSocket(runId);
    const [input, setInput] = useState('');

    const handleSend = () => {
        if (input.trim()) {
            sendMessage({ query: input });
            setInput('');
        }
    };

    return (
        <div>
            <div>
                <h2>WebSocket Messages</h2>
                <div>
                    import Message from './Message';

// ... (imports)

// ... (component definition)

                    {messages.map((msg, index) => (
                        <Message key={index} message={msg} />
                    ))}
                </div>
            </div>
            <div>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                />
                <button onClick={handleSend} disabled={!isConnected}>
                    Send
                </button>
            </div>
        </div>
    );
};

export default Chat;
