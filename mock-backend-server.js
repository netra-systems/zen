const http = require('http');
const url = require('url');

// Helper function to parse JSON body
function parseJsonBody(req) {
  return new Promise((resolve) => {
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        resolve(null); // Invalid JSON
      }
    });
  });
}

// Helper function to send JSON response with CORS
function sendJsonResponse(res, statusCode, data) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, Origin',
  });
  res.end(JSON.stringify(data));
}

const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const path = parsedUrl.pathname;
  const query = parsedUrl.query;
  const method = req.method;
  
  console.log(`${method} ${path}`, query);
  
  // Handle OPTIONS preflight requests
  if (method === 'OPTIONS') {
    res.writeHead(200, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, Origin',
    });
    res.end();
    return;
  }
  
  try {
    // Auth config endpoint
    if (path === '/auth/config' && method === 'GET') {
      return sendJsonResponse(res, 200, {
        development_mode: true,
        google_client_id: '',
        endpoints: {
          dev_login: 'http://localhost:8082/auth/dev/login'
        }
      });
    }
    
    // Dev login endpoint
    if (path === '/auth/dev/login' && method === 'POST') {
      const body = await parseJsonBody(req);
      console.log('Dev login attempt:', body);
      
      return sendJsonResponse(res, 200, {
        access_token: 'mock.jwt.token.for.testing',
        token_type: 'Bearer',
        expires_in: 3600
      });
    }
    
    // Search endpoint with SQL injection protection
    if (path === '/threads/search' && method === 'GET') {
      const q = query.q;
      console.log('Search query:', q);
      
      // Check for SQL injection attempts
      if (q && (q.includes("'") || q.includes("DROP") || q.includes("UNION") || q.includes("--"))) {
        console.log('Potential SQL injection detected:', q);
        return sendJsonResponse(res, 400, { error: 'Invalid search query' });
      }
      
      return sendJsonResponse(res, 200, { results: [], query: q });
    }
    
    // User profile endpoint
    if (path === '/api/users/profile' && method === 'GET') {
      const q = query.q;
      console.log('Profile query:', q);
      
      // Check for SQL injection attempts
      if (q && (q.includes("'") || q.includes("DROP") || q.includes("UNION") || q.includes("--"))) {
        console.log('Potential SQL injection detected in profile:', q);
        return sendJsonResponse(res, 400, { error: 'Invalid parameter' });
      }
      
      return sendJsonResponse(res, 200, { 
        id: 'test-user',
        email: 'test@example.com',
        name: 'Test User'
      });
    }
    
    // Admin users endpoint
    if (path === '/api/admin/users' && method === 'GET') {
      const q = query.q;
      console.log('Admin users query:', q);
      
      // Check authorization
      const authHeader = req.headers.authorization;
      if (!authHeader) {
        return sendJsonResponse(res, 401, { error: 'Authorization required' });
      }
      
      // Check for SQL injection attempts
      if (q && (q.includes("'") || q.includes("DROP") || q.includes("UNION") || q.includes("--"))) {
        console.log('Potential SQL injection detected in admin:', q);
        return sendJsonResponse(res, 400, { error: 'Invalid parameter' });
      }
      
      return sendJsonResponse(res, 200, { users: [] });
    }
    
    // Thread creation endpoint with XSS protection
    if (path === '/threads' && method === 'POST') {
      const body = await parseJsonBody(req);
      console.log('Create thread:', body);
      
      if (body === null) {
        return sendJsonResponse(res, 400, { error: 'Invalid JSON' });
      }
      
      // Check for XSS attempts in the request body
      const bodyStr = JSON.stringify(body);
      if (bodyStr.includes('<script>') || bodyStr.includes('javascript:') || bodyStr.includes('onerror=') || bodyStr.includes('onload=')) {
        console.log('Potential XSS detected in thread creation:', bodyStr);
        // Sanitize the input by stripping HTML tags
        const sanitizedBody = { ...body };
        if (sanitizedBody.name) {
          sanitizedBody.name = sanitizedBody.name.replace(/<[^>]*>/g, '');
        }
        if (sanitizedBody.description) {
          sanitizedBody.description = sanitizedBody.description.replace(/<[^>]*>/g, '');
        }
        
        return sendJsonResponse(res, 200, {
          id: 'mock-thread-id',
          ...sanitizedBody,
          created_at: new Date().toISOString()
        });
      }
      
      return sendJsonResponse(res, 200, {
        id: 'mock-thread-id',
        ...body,
        created_at: new Date().toISOString()
      });
    }
    
    // Profile update endpoint with CSRF protection
    if (path === '/api/users/profile' && method === 'POST') {
      const body = await parseJsonBody(req);
      console.log('Update profile:', body);
      
      if (body === null) {
        return sendJsonResponse(res, 400, { error: 'Invalid JSON' });
      }
      
      // Check Origin header for CSRF protection
      const origin = req.headers.origin;
      const allowedOrigins = ['http://localhost:3000', 'http://localhost:3010'];
      
      if (origin && !allowedOrigins.includes(origin)) {
        console.log('CSRF attempt detected - invalid origin:', origin);
        return sendJsonResponse(res, 403, { error: 'Forbidden - Invalid origin' });
      }
      
      // Check for XSS attempts
      const bodyStr = JSON.stringify(body);
      if (bodyStr.includes('<script>') || bodyStr.includes('javascript:')) {
        console.log('Potential XSS detected in profile update');
        const sanitizedBody = { ...body };
        if (sanitizedBody.name) {
          sanitizedBody.name = sanitizedBody.name.replace(/<[^>]*>/g, '');
        }
        return sendJsonResponse(res, 200, { success: true, profile: sanitizedBody });
      }
      
      return sendJsonResponse(res, 200, { success: true, profile: body });
    }
    
    // Health check
    if (path === '/health' && method === 'GET') {
      return sendJsonResponse(res, 200, { status: 'ok', timestamp: new Date().toISOString() });
    }
    
    // Default 404
    console.log(`Unhandled request: ${method} ${path}`);
    return sendJsonResponse(res, 404, { error: 'Not found' });
    
  } catch (error) {
    console.error('Server error:', error);
    return sendJsonResponse(res, 500, { error: 'Internal server error' });
  }
});

const PORT = 8082;
server.listen(PORT, () => {
  console.log(`Mock backend server running on port ${PORT}`);
  console.log('Available endpoints:');
  console.log('  GET  /health');
  console.log('  GET  /auth/config');
  console.log('  POST /auth/dev/login');
  console.log('  GET  /threads/search');
  console.log('  POST /threads');
  console.log('  GET  /api/users/profile');
  console.log('  POST /api/users/profile');
  console.log('  GET  /api/admin/users');
});