'use client';

import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function AuthErrorPage() {
  const searchParams = useSearchParams();
  const message = searchParams.get('message') || 'An error occurred during authentication';

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center max-w-md px-4">
        <h2 className="text-2xl font-semibold mb-2 text-red-600">Authentication Error</h2>
        <p className="text-gray-600 mb-6">{message}</p>
        <Link href="/login">
          <Button>Try Again</Button>
        </Link>
      </div>
    </div>
  );
}