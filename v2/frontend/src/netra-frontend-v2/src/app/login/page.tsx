'use client';

import React from 'react';

export default function LoginPage() {
  const handleGoogleLogin = () => {
    // This will be replaced with the actual Google OAuth URL
    window.location.href = 'http://localhost:8000/login/google';
  };

  return (
    <div className="flex justify-center items-center min-h-screen bg-gray-100 p-4">
      <div className="w-full max-w-md bg-white rounded-lg shadow-md overflow-hidden">
        <div className="p-6 text-center border-b">
          <h1 className="text-2xl font-bold text-gray-800">Login with Google</h1>
        </div>
        <div className="p-6">
          <button 
            onClick={handleGoogleLogin}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Login with Google
          </button>
        </div>
      </div>
    </div>
  );
}
