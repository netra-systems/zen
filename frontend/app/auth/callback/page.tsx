import { Suspense } from 'react';
import AuthCallbackClient from './client';

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-semibold mb-2">Loading...</h2>
        </div>
      </div>
    }>
      <AuthCallbackClient />
    </Suspense>
  );
}