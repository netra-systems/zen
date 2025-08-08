import { render, screen } from '@testing-library/react';
import { MessageCard } from '../MessageCard';
import { ChatMessage } from '@/types';

const mockUser = {
    name: 'Test User',
    picture: 'https://example.com/avatar.png',
};

describe('MessageCard', () => {
    it('renders a message from a sub-agent', () => {
        const message: ChatMessage = {
            event: 'chat_message',
            run_id: '1',
            data: {
                sub_agent_name: 'Test Agent',
                ai_message: 'This is a test message from the agent.',
                tools_used: ['Tool A', 'Tool B'],
            },
        };
        render(<MessageCard message={message} user={mockUser} />);
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
        expect(screen.getByText('This is a test message from the agent.')).toBeInTheDocument();
        expect(screen.getByText('Tools: Tool A, Tool B')).toBeInTheDocument();
    });

    it('renders a user message', () => {
        const message: ChatMessage = {
            event: 'chat_message',
            run_id: '2',
            data: {
                user_message: 'Hello, world!',
            },
        };
        render(<MessageCard message={message} user={mockUser} />);
        expect(screen.getByText('Hello, world!')).toBeInTheDocument();
    });

    it('renders a message with a todo list', () => {
        const message: ChatMessage = {
            event: 'chat_message',
            run_id: '3',
            data: {
                sub_agent_name: 'Test Agent',
                tool_todo_list: [{ task: 'Step 1' }, { task: 'Step 2' }],
            },
        };
        render(<MessageCard message={message} user={mockUser} />);
        expect(screen.getByText('TODO List')).toBeInTheDocument();
    });

    it('renders a message with tool errors', () => {
        const message: ChatMessage = {
            event: 'chat_message',
            run_id: '4',
            data: {
                sub_agent_name: 'Test Agent',
                tool_errors: [{ tool_name: 'Tool A', error_message: 'Something went wrong.' }],
            },
        };
        render(<MessageCard message={message} user={mockUser} />);
        expect(screen.getByText('Error in Tool A: Something went wrong.')).toBeInTheDocument();
    });
});
