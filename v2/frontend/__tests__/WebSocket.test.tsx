
import { render, screen, waitFor } from '@testing-library/react';
import useWebSocket from 'react-use-websocket';

jest.mock('react-use-websocket');

const TestComponent = () => {
  const [sendJsonMessage, lastJsonMessage, readyState] = useWebSocket('ws://localhost:8000');
  return (
    <div>
      <span>ReadyState: {readyState}</span>
    </div>
  );
};

describe('useWebSocket', () => {
  it('should return the correct values', async () => {
    const mockSendJsonMessage = jest.fn();
    const mockLastJsonMessage = {};
    const mockReadyState = 1;

    (useWebSocket as jest.Mock).mockReturnValue([
      mockSendJsonMessage,
      mockLastJsonMessage,
      mockReadyState,
    ]);

    render(<TestComponent />);

    await waitFor(() => {
      expect(screen.getByText('ReadyState: 1')).toBeInTheDocument();
    });
  });
});
