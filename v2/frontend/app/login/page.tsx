import React from 'react';
import LoginButton from './LoginButton';

export default function LoginPage() {
  return (
    <div className="flex justify-center items-center min-h-screen bg-gray-100 p-4">
      <div className="w-full max-w-md bg-white rounded-lg shadow-md overflow-hidden">
        <div className="p-6 text-center border-b">
          <h1 className="text-2xl font-bold text-gray-800">Login with Google</h1>
        </div>
        <div className="p-6">
          <LoginButton />
        </div>
      </div>
    </div>
  );
}

