import type { AppProps } from 'next/app';
import { AuthProvider } from '@/contexts/AuthContext';
import { WebSocketProvider } from '@/app/providers/WebSocketProvider';
import '@/styles/globals.css';

function MyApp({ Component, pageProps }: AppProps) {
  return (
    <AuthProvider>
      <WebSocketProvider>
        <Component {...pageProps} />
      </WebSocketProvider>
    </AuthProvider>
  );
}

export default MyApp;