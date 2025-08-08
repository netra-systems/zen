import '@testing-library/jest-dom';
import 'jest-websocket-mock';

global.fetch = jest.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve({}),
  })
) as jest.Mock;

window.HTMLElement.prototype.scrollIntoView = jest.fn();