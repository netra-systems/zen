'use client';

import { useSearchParams } from 'next/navigation';

export default function AuthErrorPage() {
  const searchParams = useSearchParams();
  const message = searchParams.get('message');

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div>
        <h1 className="text-2xl font-bold text-red-500">Authentication Error</h1>
        <p>{message || 'An unknown error occurred.'}</p>
      </div>
    </div>
  );
}
