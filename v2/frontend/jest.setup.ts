import '@testing-library/jest-dom';
import { server } from './mocks/server';
import fetchMock from 'jest-fetch-mock';

fetchMock.enableMocks();

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());