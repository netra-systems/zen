'use client';

import React from 'react';
import { useWebSocket } from '@/contexts/WebSocketContext';
import { useAuth } from '@/contexts/AuthContext';
import { AnalysisRequest } from '@/types';

const HomePage: React.FC = () => {
  const { sendMessage, lastMessage, isConnected } = useWebSocket();
  const { user, login, logout, loading } = useAuth();

  const handleSendMessage = () => {
    if (user) {
      const request: Omit<AnalysisRequest, 'type'> = {
        payload: {
          user_id: user.id,
          query: 'test query',
          workloads: [],
        },
      };
      sendMessage(request);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div style={{ padding: '20px' }}>
      <h1>Netra</h1>
      {user ? (
        <div>
          <h2>Welcome, {user.full_name || user.email}</h2>
          <p>WebSocket Connected: {isConnected ? 'Yes' : 'No'}</p>
          <button onClick={logout} style={{ marginRight: '10px' }}>Logout</button>
          <button onClick={handleSendMessage} disabled={!isConnected}>Send Test Message</button>
          {lastMessage && (
            <div style={{ marginTop: '20px' }}>
              <h3>Last Message Received:</h3>
              <pre style={{ background: '#f0f0f0', padding: '10px', borderRadius: '5px' }}>
                {JSON.stringify(lastMessage, null, 2)}
              </pre>
            </div>
          )}
        </div>
      ) : (
        <div>
          <p>Please log in to continue.</p>
          <button 
            onClick={login} 
            style={{
              padding: '10px 20px', 
              fontSize: '16px', 
              cursor: 'pointer', 
              backgroundColor: '#4285F4', 
              color: 'white', 
              border: 'none', 
              borderRadius: '5px'
            }}
          >
            Login with Google
          </button>
        </div>
      )}
    </div>
  );
};

export default HomePage;