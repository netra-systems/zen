
import { http, HttpResponse } from 'msw';

export const handlers = [
  // Mock for login
  http.post('/api/login', async ({ request }) => {
    const { username } = await request.json();
    if (username === 'testuser') {
      return HttpResponse.json({
        id: 'c7b3d8e0-5e0b-4b0f-8b3a-3b9f4b3d3b3d',
        firstName: 'John',
        lastName: 'Maverick',
        email: 'testuser@example.com',
      });
    } else {
      return new HttpResponse(null, { status: 401 });
    }
  }),

  // Mock for logout
  http.post('/api/logout', () => {
    return new HttpResponse(null, { status: 200 });
  }),

  // Mock for user settings
  http.get('/api/user/settings', () => {
    return HttpResponse.json({
      theme: 'dark',
    });
  }),

  // Mock for dashboard data
  http.get('/api/dashboard', () => {
    return HttpResponse.json({
      metrics: [
        { name: 'Metric 1', value: 123 },
        { name: 'Metric 2', value: 456 },
      ],
    });
  }),

  // Mock for DeepAgent chat
  http.post('/api/chat', async ({ request }) => {
    const { message } = await request.json();
    return HttpResponse.json({
      reply: `You said: ${message}`,
    });
  }),
];
