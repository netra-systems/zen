"use client";

import React, { useState } from 'react';

/**
 * Simple test page for Cypress testing of agent functionality
 * Bypasses complex MainChat components that cause slow compilation
 */
const TestAgentPage: React.FC = () => {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);
    
    try {
      // Make direct API call to test agent endpoints
      const response = await fetch('http://localhost:8000/api/agents/optimization', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`
        },
        body: JSON.stringify({
          message: message,
          user_id: 'test-user-id'
        })
      });

      const data = await response.json();
      setResponse(JSON.stringify(data, null, 2));
    } catch (error) {
      setResponse(`Error: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Agent Test Page</h1>
      
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '20px' }}>
          <textarea
            data-testid="message-input"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Enter your optimization request..."
            rows={4}
            style={{ width: '100%', padding: '10px' }}
          />
        </div>
        
        <button 
          type="submit" 
          data-testid="send-button"
          disabled={isProcessing || !message.trim()}
          style={{ 
            padding: '10px 20px', 
            backgroundColor: isProcessing ? '#ccc' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isProcessing ? 'not-allowed' : 'pointer'
          }}
        >
          {isProcessing ? 'Processing...' : 'Send'}
        </button>
      </form>

      {isProcessing && (
        <div data-testid="processing-indicator" style={{ marginTop: '20px' }}>
          <p>Analyzing your request...</p>
        </div>
      )}

      {response && (
        <div style={{ marginTop: '20px' }}>
          <h3>Response:</h3>
          <pre style={{ 
            backgroundColor: '#f5f5f5', 
            padding: '15px', 
            borderRadius: '4px',
            overflow: 'auto'
          }}>
            {response}
          </pre>
        </div>
      )}
    </div>
  );
};

export default TestAgentPage;