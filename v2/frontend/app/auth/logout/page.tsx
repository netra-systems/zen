'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function LogoutPage() {
  const router = useRouter();

  useEffect(() => {
    // Clear the token
    localStorage.removeItem('jwt_token');
    
    // Clear any other auth-related data if needed
    sessionStorage.clear();
    
    // Redirect to login page
    router.push('/login');
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h2 className="text-2xl font-semibold mb-2">Logging out...</h2>
        <p className="text-gray-600">You are being logged out.</p>
      </div>
    </div>
  );
}