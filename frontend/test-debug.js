const React = require('react');
const { render, screen } = require('@testing-library/react');
require('./jest.setup.js');

// Import the component
const { MessageInput } = require('./components/chat/MessageInput');

// Set up mocks
const mockUseTextareaResize = jest.fn(() => ({ rows: 3 }));
jest.mock('./components/chat/hooks/useTextareaResize', () => ({
  useTextareaResize: mockUseTextareaResize
}));

const html = render(React.createElement(MessageInput)).container.innerHTML;
console.log('Rendered HTML:', html);

const textarea = screen.getByRole('textbox');
console.log('Textarea attributes:', {
  rows: textarea.getAttribute('rows'),
  placeholder: textarea.getAttribute('placeholder')
});
