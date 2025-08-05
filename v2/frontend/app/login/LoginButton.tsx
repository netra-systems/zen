'use client';

import React from 'react';

interface LoginButtonProps {
  onClick?: () => void;
}

export default function LoginButton({ onClick }: LoginButtonProps) {
  const handleGoogleLogin = () => {
    window.location.href = 'http://localhost:8000/login/google';
  };

  return (
    <button 
      onClick={onClick || handleGoogleLogin}
      className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
    >
      Login with Google
    </button>
  );
}
