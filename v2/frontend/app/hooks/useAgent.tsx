import { useAgentStreaming } from './useAgentStreaming';
import { getToken } from '../lib/user';

export function useAgent() {
  const { addMessage, processStream, setShowThinking, ...rest } = useAgentStreaming();

  const startAgent = async (message: string) => {
    addMessage(message);
    const token = await getToken();
    if (token) {
      setShowThinking(true);
      try {
        const response = await fetch('/api/agent', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ message }),
        });

        if (!response.body) {
          throw new Error('No response body');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }
          processStream(decoder.decode(value));
        }
      } catch (error) {
        console.error('Error calling agent:', error);
      } finally {
        setShowThinking(false);
      }
    }
  };

  return { startAgent, addMessage, setShowThinking, ...rest };
}
