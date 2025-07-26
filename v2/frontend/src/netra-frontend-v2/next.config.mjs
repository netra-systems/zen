/** @type {import('next').NextConfig} */
const nextConfig = {
    async rewrites() {
      return [
        {
          source: '/api/v2/:path*',
          destination: 'http://127.0.0.1:8000/api/v2/:path*', // Proxy to Backend
        },
         {
          source: '/token',
          destination: 'http://127.0.0.1:8000/token', // Proxy to Backend
        },
      ];
    },
  };
  
  export default nextConfig;
  