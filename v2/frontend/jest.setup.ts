import 'whatwg-fetch';
import '@testing-library/jest-dom';
import fetchMock from 'jest-fetch-mock';

fetchMock.enableMocks();

window.HTMLElement.prototype.scrollIntoView = jest.fn();