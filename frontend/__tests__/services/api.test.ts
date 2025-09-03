import fetchMock from 'jest-fetch-mock';

// Simple API service for testing
class ApiService {
  private baseUrl: string;

  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async get(endpoint: string) {
    const response = await fetch(`${this.baseUrl}${endpoint}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return response.json();
  }

  async post(endpoint: string, data: any) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return response.json();
  }

  async delete(endpoint: string) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return response.ok;
  }
}

describe('API Service', () => {
  const apiService = new ApiService();

  beforeEach(() => {
    fetchMock.resetMocks();
  });

  describe('GET requests', () => {
    it('fetches data successfully', async () => {
      const mockData = { id: 1, name: 'Test' };
      fetchMock.mockResponseOnce(JSON.stringify(mockData));

      const result = await apiService.get('/api/test');

      expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/test');
      expect(result).toEqual(mockData);
    });

    it('handles GET errors', async () => {
      fetchMock.mockResponseOnce('', { status: 404 });

      await expect(apiService.get('/api/notfound')).rejects.toThrow('HTTP error! status: 404');
    });
  });

  describe('POST requests', () => {
    it('posts data successfully', async () => {
      const postData = { name: 'New Item' };
      const responseData = { id: 2, ...postData };
      fetchMock.mockResponseOnce(JSON.stringify(responseData));

      const result = await apiService.post('/api/items', postData);

      expect(fetchMock).toHaveBeenCalledWith(
        'http://localhost:8000/api/items',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(postData),
        })
      );
      expect(result).toEqual(responseData);
    });

    it('handles POST errors', async () => {
      fetchMock.mockResponseOnce('', { status: 500 });

      await expect(apiService.post('/api/items', {})).rejects.toThrow('HTTP error! status: 500');
    });
  });

  describe('DELETE requests', () => {
    it('deletes successfully', async () => {
      fetchMock.mockResponseOnce('', { status: 204 });

      const result = await apiService.delete('/api/items/1');

      expect(fetchMock).toHaveBeenCalledWith(
        'http://localhost:8000/api/items/1',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
      expect(result).toBe(true);
    });

    it('handles DELETE errors', async () => {
      fetchMock.mockResponseOnce('', { status: 403 });

      await expect(apiService.delete('/api/items/1')).rejects.toThrow('HTTP error! status: 403');
    });
  });

  it('uses custom base URL', async () => {
    const customApi = new ApiService('http://api.example.com');
    fetchMock.mockResponseOnce(JSON.stringify({ success: true }));

    await customApi.get('/test');

    expect(fetchMock).toHaveBeenCalledWith('http://api.example.com/test');
  });
});