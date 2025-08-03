import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { cn } from '@/lib/utils';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Netra - AI Workload Optimization',
  description: 'AI-Powered Workload Optimization',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={cn('min-h-screen bg-background font-sans antialiased', inter.className)}>
      
          <div className="relative flex min-h-screen flex-col">
            <div className="flex-1">{children}</div>
          </div>
      
      </body>
    </html>
  );
}