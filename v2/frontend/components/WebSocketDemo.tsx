import React, { useState } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import { WebSocketMessage, RequestModel, AnalysisRequest } from '../types/websockets';

export const WebSocketDemo: React.FC = () => {
  const { status, sendMessage, lastMessage } = useWebSocket();
  const [query, setQuery] = useState('Analyze my data');

  const handleSendMessage = () => {
    const requestModel: RequestModel = {
      id: 'req_' + Math.random().toString(36).substr(2, 9),
      user_id: 'dev-user',
      query: query,
      workloads: [
        {
          run_id: 'run_' + Math.random().toString(36).substr(2, 9),
          query: 'workload query',
          data_source: {
            source_table: 'my_table',
          },
          time_range: {
            start_time: new Date().toISOString(),
            end_time: new Date().toISOString(),
          },
        },
      ],
    };

    const analysisRequest: AnalysisRequest = { request_model: requestModel };

    const message: WebSocketMessage = {
      type: 'analysis_request',
      payload: analysisRequest,
    };

    sendMessage(message);
  };

  return (
    <div>
      <h2>WebSocket Demo</h2>
      <p>Status: {status}</p>
      <div>
        <input type="text" value={query} onChange={(e) => setQuery(e.targe.value)} />
        <button onClick={handleSendMessage} disabled={status !== 'OPEN'}>
          Send Analysis Request
        </button>
      </div>
      <h3>Last Message:</h3>
      <pre>{JSON.stringify(lastMessage, null, 2)}</pre>
    </div>
  );
};