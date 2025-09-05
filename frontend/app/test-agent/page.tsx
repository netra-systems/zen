"use client";

import React, { useState } from 'react';
import { AgentServiceV2, type AgentExecutionResult } from '@/services/agentServiceV2';

/**
 * Simple test page for Cypress testing of agent functionality
 * Bypasses complex MainChat components that cause slow compilation
 */
const TestAgentPage: React.FC = () => {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [executionResult, setExecutionResult] = useState<AgentExecutionResult | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);
    setExecutionResult(null);
    
    try {
      // Determine agent type based on message content
      let agentType: 'data' | 'optimization' | 'triage' | 'supervisor' = 'optimization'; // default for test
      
      if (message.toLowerCase().includes('data') || message.toLowerCase().includes('dataset')) {
        agentType = 'data';
      } else if (message.toLowerCase().includes('triage') || message.toLowerCase().includes('classify')) {
        agentType = 'triage';
      }

      // Use v2 Agent Service with automatic v1/v2 API selection
      const result = await AgentServiceV2.executeAgent(
        agentType,
        message,
        undefined, // no thread_id for test page
        {
          timeout: 30000, // 30 second timeout for testing
          includeMetrics: true
        }
      );

      // Store the full result for detailed display
      setExecutionResult(result);
      
      // Format response for display
      const displayData = {
        success: result.success,
        api_version: result.api_version,
        request_id: result.request_id,
        execution_result: result.result,
        metrics: result.metrics,
        warnings: result.warnings,
        error: result.error,
        error_code: result.error_code
      };

      setResponse(JSON.stringify(displayData, null, 2));
      
      // Log execution for debugging
      console.log('Agent execution completed:', {
        agent_type: agentType,
        api_version: result.api_version,
        success: result.success,
        request_id: result.request_id
      });
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setResponse(`Error: ${errorMessage}`);
      
      console.error('Agent execution failed:', {
        error: errorMessage,
        message_length: message.length
      });
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1000px', margin: '0 auto' }}>
      <h1>Agent Test Page (v2 API)</h1>
      
      <div style={{ marginBottom: '20px', padding: '10px', backgroundColor: '#e3f2fd', borderRadius: '4px' }}>
        <p><strong>v2 API Features:</strong></p>
        <ul style={{ margin: '5px 0' }}>
          <li>Request-scoped isolation for multi-user safety</li>
          <li>Automatic v1/v2 endpoint selection</li>
          <li>Enhanced error handling and metrics</li>
          <li>Unified agent types: data, optimization, triage</li>
        </ul>
      </div>
      
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Agent Request:
          </label>
          <textarea
            data-testid="message-input"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Enter your request (keywords: 'data' for data agent, 'triage' for triage agent, default: optimization)..."
            rows={4}
            style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
          />
          <small style={{ color: '#666' }}>
            Try keywords like "data analysis", "optimize costs", or "triage this issue"
          </small>
        </div>
        
        <button 
          type="submit" 
          data-testid="send-button"
          disabled={isProcessing || !message.trim()}
          style={{ 
            padding: '12px 24px', 
            backgroundColor: isProcessing ? '#ccc' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isProcessing ? 'not-allowed' : 'pointer',
            fontSize: '16px'
          }}
        >
          {isProcessing ? 'Processing...' : 'Execute Agent'}
        </button>
      </form>

      {isProcessing && (
        <div data-testid="processing-indicator" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#fff3cd', borderRadius: '4px' }}>
          <p><strong>Processing Request...</strong></p>
          <p>Using v2 Agent Service with automatic API selection</p>
        </div>
      )}

      {executionResult && (
        <div style={{ marginTop: '20px' }}>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
            <span style={{ 
              padding: '4px 8px', 
              backgroundColor: executionResult.success ? '#d4edda' : '#f8d7da',
              color: executionResult.success ? '#155724' : '#721c24',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 'bold'
            }}>
              {executionResult.success ? 'SUCCESS' : 'FAILED'}
            </span>
            <span style={{ 
              padding: '4px 8px', 
              backgroundColor: executionResult.api_version === 'v2' ? '#d1ecf1' : '#fff3cd',
              color: executionResult.api_version === 'v2' ? '#0c5460' : '#856404',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 'bold'
            }}>
              API {executionResult.api_version.toUpperCase()}
            </span>
            <span style={{ 
              padding: '4px 8px', 
              backgroundColor: '#f8f9fa',
              color: '#495057',
              borderRadius: '4px',
              fontSize: '12px'
            }}>
              ID: {executionResult.request_id}
            </span>
          </div>

          {executionResult.metrics && (
            <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#e9ecef', borderRadius: '4px' }}>
              <h4 style={{ margin: '0 0 10px 0' }}>Execution Metrics:</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px' }}>
                {Object.entries(executionResult.metrics).map(([key, value]) => (
                  <div key={key} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#007bff' }}>{value}</div>
                    <div style={{ fontSize: '12px', color: '#666', textTransform: 'capitalize' }}>
                      {key.replace(/_/g, ' ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {executionResult.warnings && executionResult.warnings.length > 0 && (
            <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#fff3cd', borderRadius: '4px', border: '1px solid #ffeeba' }}>
              <h4 style={{ margin: '0 0 10px 0', color: '#856404' }}>Warnings:</h4>
              <ul style={{ margin: 0, paddingLeft: '20px' }}>
                {executionResult.warnings.map((warning, index) => (
                  <li key={index} style={{ color: '#856404' }}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {response && (
        <div style={{ marginTop: '20px' }}>
          <h3>Full Response:</h3>
          <pre style={{ 
            backgroundColor: '#f8f9fa', 
            padding: '15px', 
            borderRadius: '4px',
            overflow: 'auto',
            fontSize: '12px',
            border: '1px solid #dee2e6'
          }}>
            {response}
          </pre>
        </div>
      )}
    </div>
  );
};

export default TestAgentPage;