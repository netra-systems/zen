import '@testing-library/jest-dom';
import 'jest-websocket-mock';

window.HTMLElement.prototype.scrollIntoView = jest.fn();
