import { renderHook, act } from '@testing-library/react';
import { useAgent } from '../app/hooks/useAgent';
import { agent } from '../app/services/agent/Agent';

jest.mock('../app/services/agent/Agent', () => ({
    agent: {
        initialize: jest.fn(),
        start: jest.fn(),
        stop: jest.fn(),
        subscribe: jest.fn(() => () => {}),
    },
}));

describe('useAgent', () => {
    it('should subscribe to the agent and start it', () => {
        const { result } = renderHook(() => useAgent());
        act(() => {
            result.current.startAgent('test message', []);
        });
        expect(agent.subscribe).toHaveBeenCalled();
        expect(agent.start).toHaveBeenCalledWith('test message', []);
    });
});
