
import React from 'react';
import { useWebSocket } from '@/contexts/WebSocketProvider';
import { useAuth } from '@/contexts/AuthContext';

const HomePage: React.FC = () => {
  const { sendMessage } = useWebSocket();
  const { user, login, logout } = useAuth();

  const handleSendMessage = () => {
    sendMessage({ text: 'Hello from the client!' });
  };

  return (
    <div>
      <h1>Welcome to the WebSocket Example</h1>
      {user ? (
        <div>
          <p>Welcome, {user.email}</p>
          <button onClick={logout}>Logout</button>
          <button onClick={handleSendMessage}>Send Message</button>
        </div>
      ) : (
        <button onClick={login}>Login as Dev</button>
      )}
    </div>
  );
};

export default HomePage;
