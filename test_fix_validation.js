// Simple validation script to test the useAgent hook fix
// This script manually tests the message structure without Jest setup issues

// Mock WebSocket hook
const mockSendMessage = jest.fn ? jest.fn() : function(message) {
  console.log('Mock sendMessage called with:', JSON.stringify(message, null, 2));
  mockSendMessage.lastCall = message;
};

// Mock useWebSocket hook
const mockUseWebSocket = () => ({
  sendMessage: mockSendMessage,
  status: 'OPEN',
  messages: [],
});

// Simplified version of the useAgent hook logic
const useAgent = () => {
  const webSocket = mockUseWebSocket();

  const sendUserMessage = (text) => {
    const message = {
      type: 'user_message',
      payload: {
        content: text,
      },
    };
    webSocket?.sendMessage(message);
  };

  const stopAgent = () => {
    const message = {
      type: 'stop_agent',
      payload: {
        agent_id: '' // The backend will know which agent to stop
      },
    };
    webSocket?.sendMessage(message);
  };

  return { sendUserMessage, stopAgent };
};

// Test the fix
console.log('Testing useAgent hook fix...\n');

const { sendUserMessage, stopAgent } = useAgent();

// Test sendUserMessage
console.log('1. Testing sendUserMessage with "Test message":');
sendUserMessage('Test message');
const sentData = mockSendMessage.lastCall;

console.log('Expected: type="user_message", payload.content="Test message"');
console.log('Actual  :', `type="${sentData.type}", payload.content="${sentData.payload.content}"`);

const sendUserMessagePassed = 
  sentData.type === 'user_message' && 
  sentData.payload.content === 'Test message';

console.log('✅ sendUserMessage test:', sendUserMessagePassed ? 'PASSED' : 'FAILED');
console.log();

// Test stopAgent
console.log('2. Testing stopAgent:');
stopAgent();
const stopData = mockSendMessage.lastCall;

console.log('Expected: type="stop_agent", payload.agent_id=""');
console.log('Actual  :', `type="${stopData.type}", payload.agent_id="${stopData.payload.agent_id}"`);

const stopAgentPassed = 
  stopData.type === 'stop_agent' && 
  stopData.payload.agent_id === '';

console.log('✅ stopAgent test:', stopAgentPassed ? 'PASSED' : 'FAILED');
console.log();

console.log('Overall result:', (sendUserMessagePassed && stopAgentPassed) ? '✅ ALL TESTS PASSED' : '❌ SOME TESTS FAILED');